# coding=utf-8
import os
from subprocess import call
from time import sleep
from unittest import TestCase

from nose.tools import (assert_equal, assert_not_equal, assert_in,
                        assert_true, assert_regexp_matches, timed)
from webtest import TestApp

from tests.utils import uci_get, uci_set, uci_commit
import foris


# dict of texts that are used to determine returned stated etc.
RESPONSE_TEXTS = {
    'form_invalid': "údajů nejsou platné",
    'form_saved': "Nastavení bylo úspěšně",
    'invalid_old_pw': "původní heslo je neplatné",
    'password_changed': "Heslo bylo úspěšně uloženo.",
    'passwords_not_equal': "Hesla se neshodují.",
}


class TestInitException(Exception):
    pass


class ForisTest(TestCase):
    app = None
    config_directory = "/tmp/test-etc_config/"

    @classmethod
    def setUpClass(cls):
        # load configs and monkey-patch env so Nuci uses them
        cls.restore_config()
        os.environ["NUCI_TEST_CONFIG_DIR"] = cls.config_directory
        os.environ["NUCI_DONT_RESTART"] = "1"
        # initialize Foris WSGI app
        args = cls.make_args()
        cls.app = TestApp(foris.prepare_main_app(args))

    @classmethod
    def tearDownClass(cls):
        call(["rm", "-rf", cls.config_directory])

    @classmethod
    def restore_config(cls):
        call(["rm", "-rf", cls.config_directory])
        call(["mkdir", cls.config_directory])
        if call(["tar", "xzf", "/www2/tests/configs.tar.gz", "-C", cls.config_directory]) > 0:
            raise TestInitException("Cannot extract configs.")

    @classmethod
    def set_foris_password(cls, password):
        from beaker.crypto import pbkdf2
        encrypted_pwd = pbkdf2.crypt(password)
        if not (uci_set("foris.auth", "config", cls.config_directory)
                and uci_set("foris.auth.password", encrypted_pwd, cls.config_directory)
                and uci_commit(cls.config_directory)):
            raise TestInitException("Cannot set Foris password.")

    @classmethod
    def mark_wizard_completed(cls):
        if not (uci_set("foris.wizard", "config", cls.config_directory)
                and uci_set("foris.wizard.allowed_step_max", 8, cls.config_directory)
                and uci_commit(cls.config_directory)):
            raise TestInitException("Cannot mark Wizard as completed.")

    @staticmethod
    def make_args():
        parser = foris.get_arg_parser()
        args = parser.parse_args([])
        return args

    @classmethod
    def login(cls, password):
        login_response = cls.app.post("/", {'password': password}).maybe_follow()
        assert_equal(login_response.request.path, "//config/")


class TestConfig(ForisTest):
    password = "123465"

    @classmethod
    def setUpClass(cls):
        super(TestConfig, cls).setUpClass()
        cls.set_foris_password(cls.password)
        cls.mark_wizard_completed()
        cls.login(cls.password)

    def test_login(self):
        # we should be logged in now by the setup
        assert_equal(self.app.get("/config/").status_int, 200)
        # log out and check we're on homepage
        assert_equal(self.app.get("/logout").follow().request.path, "/")
        # check we are not allowed into config anymore
        assert_equal(self.app.get("/config/").follow().request.path, "/")
        # login again
        self.login(self.password)

    def test_failed_login(self):
        assert_equal(self.app.get("/logout").follow().request.path, "/")
        res = self.app.post("/", {
            'password': self.password + "fail"
        }).maybe_follow()
        # we should have been redirected
        assert_equal(res.request.path, "/")
        # thus we should not be able to get into config
        assert_equal(self.app.get("/config/").maybe_follow().request.path, "/")
        # login again
        self.login(self.password)

    def test_tab_about(self):
        # look for serial number
        about_page = self.app.get("/config/about/")
        assert_equal(about_page.status_int, 200)
        # naive assumption - router's SN should be at least from 0x500000000 - 0x500F00000
        assert_in("<td>214", about_page.body)

    def test_tab_password(self):
        page = self.app.get("/config/password/")

        def test_pw_submit(old, new, validation, should_change, expect_text=None):
            old_pw = uci_get("foris.auth.password", self.config_directory)
            form = page.forms['main-form']
            form.set("old_password", old)
            form.set("password", new)
            form.set("password_validation", validation)
            res = form.submit().maybe_follow()
            assert_equal(res.status_int, 200)
            new_pw = uci_get("foris.auth.password", self.config_directory)
            if should_change:
                assert_not_equal(old_pw, new_pw)
            else:
                assert_equal(old_pw, new_pw)
            if expect_text:
                assert_in(expect_text, res)

        # incorrect old password must fail
        test_pw_submit("bad" + self.password, self.password + "new", self.password + "new",
                       False, RESPONSE_TEXTS['invalid_old_pw'])
        # passwords must be equal
        test_pw_submit(self.password, self.password + "a", self.password + "b",
                       False, RESPONSE_TEXTS['passwords_not_equal'])
        # finally try correct input
        new_password = self.password + "new"
        test_pw_submit(self.password, new_password, new_password,
                       True, RESPONSE_TEXTS['password_changed'])
        self.password = new_password

    def test_tab_wan(self):
        page = self.app.get("/config/wan/")
        assert_equal(page.status_int, 200)

        form = page.forms['main-form']
        form['proto'] = "static"

        submit = form.submit(headers={'X-Requested-With': "XMLHttpRequest"})
        assert_true(submit.body.lstrip().startswith("<form"))

        # try invalid submission of the form
        form = submit.forms['main-form']
        invalid = form.submit()
        assert_in(RESPONSE_TEXTS['form_invalid'], invalid)

        # fill the form returned
        form = invalid.forms['main-form']
        addr, mask, gw\
            = form['ipaddr'], form['netmask'], form['gateway'] \
            = "10.0.0.1", "255.0.0.0", "10.0.0.10"
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        assert_equal(uci_get("network.wan.ipaddr", self.config_directory), addr)
        assert_equal(uci_get("network.wan.netmask", self.config_directory), mask)
        assert_equal(uci_get("network.wan.gateway", self.config_directory), gw)

    def test_registration_code(self):
        res = self.app.get("/config/about/ajax?action=registration_code",
                           headers={'X-Requested-With': "XMLHttpRequest"})
        payload = res.json
        assert_true(payload['success'])
        # check that code is not empty
        assert_regexp_matches(payload['data'], r"[0-9A-F]{8}")


class TestWizard(ForisTest):
    """
    Test all Wizard steps.

    These tests are not comprehensive, test cases cover only few simple
    "works when it should" and "doesn't work when it shouldn't" situations.
    It doesn't mean that if all the test passed, there are not some errors
    in form handling. Such cases should be tested by unit tests to save time.

    Note: nose framework is required in this test, because the tests
    MUST be executed in the correct order (= alphabetical).
    """

    def __init__(self, *args, **kwargs):
        super(TestWizard, self).__init__(*args, **kwargs)
        self.password = "123456"

    def _test_wizard_step(self, number, max_allowed=None):
        max_allowed = max_allowed or number
        # test we are not allowed any further
        page = self.app.get("/wizard/step/%s" % (max_allowed + 1)).maybe_follow()
        assert_equal(page.request.path, "//wizard/step/%s" % max_allowed)
        # test that we are allowed where it's expected
        page = self.app.get("/wizard/step/%s" % number)
        assert_equal(page.status_int, 200)
        return page

    def test_step_0(self):
        # main page should redirect to Wizard index
        home = self.app.get("/").follow()
        assert_equal(home.request.path, "//wizard/")

    def test_step_1(self):
        self._test_wizard_step(1)
        # non-matching PWs
        wrong_input = self.app.post("/wizard/step/1", {
            'password': "123456",
            'password_validation': "111111",
            # do not send 'set_system_pw'
        })
        assert_equal(wrong_input.status_int, 200)
        assert_in(RESPONSE_TEXTS['form_invalid'], wrong_input.body)
        # good input
        good_input = self.app.post("/wizard/step/1", {
            'password': self.password,
            'password_validation': self.password,
            # do not send 'set_system_pw'
        }).follow()
        assert_equal(good_input.status_int, 200)
        assert_equal(good_input.request.path, "//wizard/step/2")

    def test_step_2(self):
        page = self._test_wizard_step(2)
        submit = page.forms['main-form'].submit().follow()
        assert_equal(submit.status_int, 200, submit.body)
        assert_equal(submit.request.path, "//wizard/step/3")

    def test_step_3(self):
        self._test_wizard_step(3)

        def check_connection(url):
            res = self.app.get(url)
            data = res.json
            assert_true(data['success'])
            assert_in(data['result'], ['ok', 'no_dns', 'no_connection'])

        # this also enables the next step
        check_connection("/wizard/step/3/ajax?action=check_connection")
        check_connection("/wizard/step/3/ajax?action=check_connection_noforward")

    def test_step_4(self):
        self._test_wizard_step(4)
        # WARN: only a case when NTP sync works is tested
        res = self.app.get("/wizard/step/4/ajax?action=ntp_update")
        data = res.json
        assert_true(data['success'])

    @timed(40)
    def test_step_5(self):
        # This test must be @timed with some reasonable timeout to check
        # that the loop for checking updater status does not run infinitely.
        self._test_wizard_step(5)

        # start the updater on background - also enables next step
        res = self.app.get("/wizard/step/5/ajax?action=run_updater")
        assert_true(res.json['success'])

        def check_updater():
            updater_res = self.app.get("/wizard/step/5/ajax?action=updater_status")
            data = updater_res.json
            assert_true(data['success'])
            return data

        check_result = check_updater()
        while check_result['status'] == "running":
            sleep(2)
            check_result = check_updater()

        assert_equal(check_result['status'], "done")

    def test_step_6(self):
        page = self._test_wizard_step(6)
        submit = page.forms['main-form'].submit().follow()
        assert_equal(submit.status_int, 200)
        assert_equal(submit.request.path, "//wizard/step/7")

    def test_step_7(self):
        page = self._test_wizard_step(7)
        form = page.forms['main-form']
        form.set("wifi_enabled", True, 1)  # index 1 contains "1"
        form.set("ssid", "Valid SSID")
        form.set("key", "validpassword")
        submit = form.submit()
        submit = submit.follow()
        assert_equal(submit.status_int, 200)
        assert_equal(submit.request.path, "//wizard/step/8")

    def test_step_8(self):
        # test that we are allowed where it's expected
        page = self.app.get("/wizard/step/8")
        assert_equal(page.status_int, 200)
        assert_regexp_matches(page.body, r"activation-code\">[0-9A-F]{8}",
                              "Activation code not found in last step.")

    def test_step_nonexist(self):
        self.app.get("/wizard/step/9", status=404)

    def test_wizard_set_password(self):
        self.app.get("/logout")
        assert_equal(self.app.get("/config/").follow().request.path, "/")
        assert_equal(self.app.get("/wizard/").follow().request.path, "/")


class TestWizardSkip(ForisTest):
    def __init__(self, *args, **kwargs):
        super(TestWizardSkip, self).__init__(*args, **kwargs)
        self.password = "123456"

    def test_skip_wizard(self):
        # go to first page to init Wizard
        assert_equal(self.app.get("/").follow().request.path, "//wizard/")
        # set password
        good_input = self.app.post("/wizard/step/1", {
            'password': self.password,
            'password_validation': self.password,
            # do not send 'set_system_pw'
        }).follow()
        assert_equal(good_input.status_int, 200)
        assert_equal(good_input.request.path, "//wizard/step/2")
        # try to skip wizard
        assert_equal(self.app.get("/wizard/skip").follow().request.path, "//config/")
        # logout
        assert_equal(self.app.get("/logout").follow().request.path, "/")
        # try to get back into wizard
        assert_equal(self.app.get("/wizard/step/2").follow().request.path, "/")