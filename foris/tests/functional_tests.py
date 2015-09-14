# coding=utf-8
import re
from subprocess import call
from tempfile import NamedTemporaryFile
from unittest import TestCase

from mock import patch
from nose.tools import (assert_equal, assert_not_equal, assert_in,
                        assert_greater, assert_less,
                        assert_true, assert_false,
                        assert_regexp_matches)
from webtest import TestApp, Upload

import foris.core
from foris.nuci.client import StaticNetconfConnection

from .utils import uci_get, uci_set, uci_commit, uci_is_empty

# dict of texts that are used to determine returned stated etc.
RESPONSE_TEXTS = {
    'config_restored': "Nastavení bylo úspěšně obnoveno.",
    'form_invalid': "údajů nejsou platné",
    'form_saved': "Nastavení bylo úspěšně",
    'invalid_old_pw': "původní heslo je neplatné",
    'password_changed': "Heslo bylo úspěšně uloženo.",
    'passwords_not_equal': "Hesla se neshodují.",
}

# header for XHR (AJAX requests)
XHR_HEADERS = {'X-Requested-With': "XMLHttpRequest"}


class TestInitException(Exception):
    pass


class ForisTest(TestCase):
    app = None
    config_directory = "/tmp/test-etc_config/"

    @classmethod
    def setUpClass(cls):
        # load configs and monkey-patch env so Nuci uses them
        cls.restore_config()
        StaticNetconfConnection.enable_test_environment(cls.config_directory)
        # initialize Foris WSGI app
        args = cls.make_args()
        cls.app = TestApp(foris.core.prepare_main_app(args))

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
        StaticNetconfConnection._connect()

    @classmethod
    def mark_wizard_completed(cls):
        if not (uci_set("foris.wizard", "config", cls.config_directory)
                and uci_set("foris.wizard.allowed_step_max", 9, cls.config_directory)
                and uci_commit(cls.config_directory)):
            raise TestInitException("Cannot mark Wizard as completed.")
        StaticNetconfConnection._connect()

    @staticmethod
    def make_args():
        parser = foris.core.get_arg_parser()
        args = parser.parse_args([])
        return args

    @classmethod
    def login(cls, password):
        page = cls.app.get("/")
        login_form = page.forms[0]
        login_form.set("password", password)
        login_response = login_form.submit().maybe_follow()
        assert_equal(login_response.request.path, "//config/")

    def uci_get(self, path):
        return uci_get(path, self.config_directory)

    def uci_is_empty(self, path):
        return uci_is_empty(path, self.config_directory)

    def uci_set(self, path, value):
        return uci_set(path, value, self.config_directory)

    def uci_commit(self):
        return uci_commit(self.config_directory)

    def check_uci_val(self, path, value):
        assert_equal(self.uci_get(path), value)


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

    def test_tab_password(self):
        page = self.app.get("/config/password/")

        def test_pw_submit(old, new, validation, should_change, expect_text=None):
            old_pw = self.uci_get("foris.auth.password")
            form = page.forms['main-form']
            form.set("old_password", old)
            form.set("password", new)
            form.set("password_validation", validation)
            res = form.submit().maybe_follow()
            assert_equal(res.status_int, 200)
            new_pw = self.uci_get("foris.auth.password")
            if expect_text:
                assert_in(expect_text, res)
            if should_change:
                assert_not_equal(old_pw, new_pw)
            else:
                assert_equal(old_pw, new_pw)

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
        form.set("proto", "static", 1)
        form.set("custom_mac", True, 1)

        submit = form.submit(headers=XHR_HEADERS)
        assert_true(submit.body.lstrip().startswith("<form"))

        # try invalid submission of the form
        form = submit.forms['main-form']
        invalid = form.submit()
        assert_in(RESPONSE_TEXTS['form_invalid'], invalid)

        # fill the form returned
        form = invalid.forms['main-form']
        addr, mask, gw, macaddr\
            = form['ipaddr'], form['netmask'], form['gateway'], form['macaddr'] \
            = "10.0.0.1", "255.0.0.0", "10.0.0.10", "01:23:45:67:89:af"
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        assert_equal(self.uci_get("network.wan.ipaddr"), addr)
        assert_equal(self.uci_get("network.wan.netmask"), mask)
        assert_equal(self.uci_get("network.wan.gateway"), gw)
        assert_equal(self.uci_get("network.wan.macaddr"), macaddr)

    def test_tab_dns(self):
        page = self.app.get("/config/dns/")
        form = page.forms['main-form']

        # check form for forwarding upstream
        default_state = self.uci_get("unbound.server.forward_upstream")
        test_state = not bool(int(default_state))
        form.set("forward_upstream", test_state, 1)  # index 1 contains "1"
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        new_state = self.uci_get("unbound.server.forward_upstream")
        assert_equal(str(int(test_state)), new_state)

        res = self.app.get("/config/dns/ajax?action=check-connection", headers=XHR_HEADERS)
        data = res.json
        assert_true(data['success'])
        assert_equal(len(data['check_results']), 6)  # we have 6 checks

        # tests need working connection with IPv4 & IPv6 connectivity
        for check, result in data['check_results'].iteritems():
            assert_true(result, "'%s' check result is not True" % check)

    def test_tab_lan(self):
        page = self.app.get("/config/lan/")
        form = page.forms['main-form']

        old_ip = self.uci_get("network.lan.ipaddr")
        form['lan_ipaddr'] = "192.168.1."
        invalid = form.submit()
        assert_in(RESPONSE_TEXTS['form_invalid'], invalid)
        # nothing should change
        self.check_uci_val("network.lan.ipaddr", old_ip)

        # DHCP is by default enabled, change IP and disable it
        try:
            assert_true(self.uci_is_empty("dhcp.lan.ignore"))
        except AssertionError:
            self.check_uci_val("dhcp.lan.ignore", "0")
        form = invalid.forms['main-form']
        expected_ip = "192.168.1.2"
        form['lan_ipaddr'] = expected_ip
        form.set("dhcp_enabled", False, 1)
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        self.check_uci_val("dhcp.lan.ignore", "1")
        self.check_uci_val("network.lan.ipaddr", expected_ip)

    def test_tab_wifi(self):
        page = self.app.get("/config/wifi/")
        form = page.forms['main-form']

        # check that radio0 is really disabled
        self.check_uci_val("wireless.radio0.disabled", "1")

        # invalid input
        old_ssid = self.uci_get("wireless.@wifi-iface[0].ssid")
        form.set("wifi_enabled", True, 1)  # index 1 contains "1"
        invalid = form.submit()
        assert_in(RESPONSE_TEXTS['form_invalid'], invalid.body)
        self.check_uci_val("wireless.@wifi-iface[0].ssid", old_ssid)

        # valid input
        form = page.forms['main-form']
        form.set("wifi_enabled", True, 1)
        expected_ssid = "Valid SSID"
        expected_key = "validpassword"
        form.set("ssid", expected_ssid)
        form.set("key", expected_key)
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        self.check_uci_val("wireless.@wifi-iface[0].ssid", expected_ssid)
        self.check_uci_val("wireless.@wifi-iface[0].key", expected_key)
        self.check_uci_val("wireless.radio0.disabled", "0")

    def test_tab_syspwd(self):
        page = self.app.get("/config/system-password/")
        form = page.forms['main-form']
        # we don't want to change system password, just check
        # that it can't be submitted with unequal fields
        form.set("password", "123456")
        form.set("password_validation", "111111")
        submit = form.submit()
        assert_in(RESPONSE_TEXTS['passwords_not_equal'], submit.body)

    def test_tab_maintenance_notifications(self):
        page = self.app.get("/config/maintenance/")
        # test notifications form - SMTP is by default disabled
        self.check_uci_val("user_notify.smtp.enable", "0")

        # try submitting with notifications disabled
        form = page.forms['notifications-form']
        form.set("reboot_time", "08:42")
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        self.check_uci_val("user_notify.reboot.time", "08:42")

        # enable smtp
        form = submit.forms['notifications-form']
        form.set("enable_smtp", True, 1)
        submit = form.submit(headers=XHR_HEADERS)

        # submit with missing from and to
        form = submit.forms['notifications-form']
        form.set('use_turris_smtp', "1")
        submit = form.submit()
        assert_in(RESPONSE_TEXTS['form_invalid'], submit.body)

        # submit valid form with Turris SMTP
        form = submit.forms['notifications-form']
        expected_sender = "router.turris"
        expected_to = "franta.novak@nic.cz"
        form.set('use_turris_smtp', "1")
        form.set('to', expected_to)
        form.set('sender_name', expected_sender)
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        self.check_uci_val("user_notify.smtp.enable", "1")
        self.check_uci_val("user_notify.smtp.use_turris_smtp", "1")
        self.check_uci_val("user_notify.smtp.to", expected_to)
        self.check_uci_val("user_notify.smtp.sender_name", expected_sender)

        # switch to custom SMTP (expect fail)
        form = submit.forms['notifications-form']
        form.set('use_turris_smtp', "0")
        submit = form.submit()
        assert_in(RESPONSE_TEXTS['form_invalid'], submit.body)

        # submit valid form with custom SMTP
        form = submit.forms['notifications-form']
        expected_to = "franta.novak@nic.cz"
        expected_from = "pepa.novak@nic.cz"
        expected_server = "smtp.example.com"
        expected_port = "25"
        form.set('use_turris_smtp', "0")
        form.set('server', expected_server)
        form.set('port', expected_port)
        form.set('to', expected_to)
        form.set('from', expected_from)
        submit = form.submit().follow()
        assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        self.check_uci_val("user_notify.smtp.enable", "1")
        self.check_uci_val("user_notify.smtp.use_turris_smtp", "0")
        self.check_uci_val("user_notify.smtp.server", expected_server)
        self.check_uci_val("user_notify.smtp.port", expected_port)
        self.check_uci_val("user_notify.smtp.to", expected_to)
        self.check_uci_val("user_notify.smtp.from", expected_from)

    def test_tab_maintenance_backups(self):
        # check testing value
        self.check_uci_val("test.test.test", "1")
        page = self.app.get("/config/maintenance/")
        # check that backup can be downloaded
        backup = self.app.get("/config/maintenance/action/config-backup")
        # check that it's huffman coded Bzip
        assert_equal(backup.body[0:3], "BZh")
        backup_len = len(backup.body)
        assert_greater(backup_len, 15000)
        assert_less(backup_len, 17000)

        # alter testing value
        self.uci_set("test.test.test", "0")
        self.uci_commit()
        self.check_uci_val("test.test.test", "0")

        # submit config restore form without file
        form = page.forms['restore-form']
        submit = form.submit()
        assert_in(RESPONSE_TEXTS['form_invalid'], submit.body)

        backup_file = NamedTemporaryFile()
        # restore backup
        try:
            # save backup to file
            backup_file.write(backup.body)
            form = page.forms['restore-form']
            form['backup_file'] = Upload(backup_file.name)
            submit = form.submit().follow()
            assert_in(RESPONSE_TEXTS['config_restored'], submit.body)
            # check that testing value was restored
            self.check_uci_val("test.test.test", "1")
        finally:
            backup_file.close()

        # check that reboot button is present
        assert_in('href="/config/maintenance/action/reboot"', page.body)

    def test_tab_updater(self):
        possible_lists = ["luci-controls", "nas", "printserver", "netutils",
                          "shell-utils"]
        default_enabled = ["luci-controls", "nas", "printserver", "netutils"]
        # check for value from default config
        self.check_uci_val("updater.pkglists.lists", " ".join(default_enabled))
        page = self.app.get("/config/updater/")
        form = page.forms['main-form']

        # check that enabled lists are checked
        for l in default_enabled:
            enabled = form.get("install_%s" % l, index=1).checked
            assert_true(enabled, "'%s' list should by enabled")

        # check that enabled lists are not checked
        default_disabled = set(possible_lists).difference(default_enabled)
        for l in default_disabled:
            enabled = form.get("install_%s" % l, index=1).checked
            assert_false(enabled, "'%s' list should by disabled")

        # disable all lists
        for l in possible_lists:
            form.set("install_%s" % l, False, 1)

        # select shell-utils and netutils
        form.set("install_shell-utils", True, 1)
        form.set("install_netutils", True, 1)
        with patch("nuci.client.check_updates") as check_updates_mock:
            check_updates_mock.return_value = True
            submit = form.submit().follow()
            assert_in(RESPONSE_TEXTS['form_saved'], submit.body)
        self.check_uci_val("updater.pkglists.lists", "netutils shell-utils")

    def test_tab_about(self):
        # look for serial number
        about_page = self.app.get("/config/about/")
        assert_equal(about_page.status_int, 200)
        assert_regexp_matches(about_page.body, r"<td>Turris - RTRS0[12]</td>",
                              "This test suite is not adjusted for this device.")
        sn_match = re.search(r"<td>(\d+)</td>", about_page.body)
        assert_true(sn_match)
        try:
            sn = int(sn_match.group(1))
        except ValueError:
            raise AssertionError("Router serial number is not integer.")
        # should work on routers from first production Turris 1.0 till new Turris 1.1
        assert_greater(sn, 0x499999999)
        assert_less(sn, 0x900F00000)

    def test_registration_code(self):
        res = self.app.get("/config/about/ajax?action=registration_code",
                           headers=XHR_HEADERS)
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
        page = self._test_wizard_step(1)
        # non-matching PWs
        form = page.forms['main-form']
        form.set("password", "123456")
        form.set("password_validation", "111111")
        wrong_input = form.submit()
        assert_equal(wrong_input.status_int, 200)
        assert_in(RESPONSE_TEXTS['form_invalid'], wrong_input.body)
        # good input
        form = wrong_input.forms['main-form']
        form.set('password', self.password)
        form.set('password_validation', self.password)
        good_input = form.submit().follow()
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

    def test_step_5(self):
        # This test must be @timed with some reasonable timeout to check
        # that the loop for checking updater status does not run infinitely.
        self._test_wizard_step(5)

        # start the updater on background - also enables next step
        # mock the method for starting the updater, we don't want to really run it
        # maybe it'd be better to patch later and test if the RPC for update is really called
        with patch("nuci.client.check_updates") as check_updates_mock:
            check_updates_mock.return_value = True
            res = self.app.get("/wizard/step/5/ajax?action=run_updater")
            assert_true(res.json['success'])

        with patch("nuci.client.get_updater_status") as updater_status_mock:
            def check_updater():
                updater_res = self.app.get("/wizard/step/5/ajax?action=updater_status")
                data = updater_res.json
                assert_true(data['success'])
                return data

            # simulate running updater in "examine" state
            updater_status_mock.return_value = "running", "examine", []
            check_result = check_updater()
            assert_equal(check_result['status'], "running")

            # simulate completed update
            updater_status_mock.return_value = "done", None, []
            check_result = check_updater()
            assert_equal(check_result['status'], "done")

    def test_step_6(self):
        # patch updater status to always allow the next step
        with patch("nuci.client.get_updater_status") as updater_status_mock:
            updater_status_mock.return_value = "done", None, []
            page = self.app.get("/wizard/step/6").maybe_follow()
            assert_equal(page.request.path, "//wizard/step/7")
            assert_equal(page.status_int, 200)

    def test_step_7(self):
        page = self._test_wizard_step(7)
        submit = page.forms['main-form'].submit().follow()
        assert_equal(submit.status_int, 200)
        assert_equal(submit.request.path, "//wizard/step/8")

    def test_step_8(self):
        page = self._test_wizard_step(8)
        form = page.forms['main-form']
        form.set("wifi_enabled", True, 1)  # index 1 contains "1"
        form.set("ssid", "Valid SSID")
        form.set("key", "validpassword")
        submit = form.submit()
        submit = submit.follow()
        assert_equal(submit.status_int, 200)
        assert_equal(submit.request.path, "//wizard/step/9")

    def test_step_9(self):
        # test that we are allowed where it's expected
        page = self.app.get("/wizard/step/9")
        assert_equal(page.status_int, 200)
        assert_regexp_matches(page.body, r"activation-code\">[0-9A-F]{8}",
                              "Activation code not found in last step.")

    def test_step_nonexist(self):
        self.app.get("/wizard/step/10", status=404)

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
        page = self.app.get("/wizard/step/1").maybe_follow()
        form = page.forms['main-form']
        form.set('password', self.password)
        form.set('password_validation', self.password)
        good_input = form.submit().follow()
        assert_equal(good_input.status_int, 200)
        assert_equal(good_input.request.path, "//wizard/step/2")
        # try to skip wizard
        assert_equal(self.app.get("/wizard/skip").follow().request.path, "//config/")
        # logout
        assert_equal(self.app.get("/logout").follow().request.path, "/")
        # try to get back into wizard
        assert_equal(self.app.get("/wizard/step/2").follow().request.path, "/")
