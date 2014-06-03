# coding=utf-8
import json
import os
from subprocess import call
from unittest import TestCase

from nose.tools import assert_equal, assert_in, assert_true, nottest
from webtest import TestApp

import foris


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
        if not (call(["uci", "-c", cls.config_directory, "set", "foris.auth=config"]) == 0
                and call(["uci", "-c", cls.config_directory, "set", "foris.auth.password=%s" % encrypted_pwd]) == 0
                and call(["uci", "-c", cls.config_directory, "commit"]) == 0):
            raise TestInitException("Cannot set Foris password.")

    @classmethod
    def mark_wizard_completed(cls):
        if not (call(["uci", "-c", cls.config_directory, "set", "foris.wizard=config"]) == 0
                and call(["uci", "-c", cls.config_directory, "set", "foris.wizard.allowed_step_max=%s" % 8]) == 0
                and call(["uci", "-c", cls.config_directory, "commit"]) == 0):
            raise TestInitException("Cannot mark Wizard as completed.")

    @staticmethod
    def make_args():
        parser = foris.get_arg_parser()
        args = parser.parse_args([])
        return args


class TestConfig(ForisTest):
    password = "123465"

    @classmethod
    def setUpClass(cls):
        super(TestConfig, cls).setUpClass()
        cls.set_foris_password(cls.password)
        cls.mark_wizard_completed()
        cls.login()

    @classmethod
    def login(cls):
        # expect that login redirects back to itself and then to config
        login_response = cls.app.post("/", {'password': cls.password}).maybe_follow()
        assert_equal(login_response.request.path, "//config/")

    def test_login(self):
        # we should be logged in now by the setup
        assert_equal(self.app.get("/config/").status_int, 200)
        # log out and check we're on homepage
        assert_equal(self.app.get("/logout").follow().request.path, "/")
        # check we are not allowed into config anymore
        assert_equal(self.app.get("/config/").follow().request.path, "/")
        # login again
        self.login()

    def test_tab_about(self):
        # look for serial number
        about_page = self.app.get("/config/about/")
        assert_equal(about_page.status_int, 200)
        # naive assumption - router's SN should be at least from 0x500000000 - 0x500F00000
        assert_in("<td>214", about_page.body)

    def test_registration_code(self):
        res = self.app.get("/config/about/ajax?action=registration_code")
        payload = json.loads(res.body)
        assert_true(payload['success'])
        # check that code is not empty
        assert_true(payload['data'])


class TestWizard(ForisTest):
    """
    Test all Wizard steps.

    Note: nose framework is required in this test, because the tests
    MUST be executed in the correct order (= alphabetical).
    """

    @classmethod
    def setUpClass(cls):
        super(TestWizard, cls).setUpClass()

    def _test_wizard_step(self, number):
        # test we are not allowed any further
        page = self.app.get("/wizard/step/2").maybe_follow()
        assert_equal(page.request.path, "//wizard/step/%s" % number)
        # test that we are allowed where it's expected
        page = self.app.get("/wizard/step/1")
        assert_equal(page.status_int, 200)

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
        assert_in("nejsou platné", wrong_input.body)
        # good input
        good_input = self.app.post("/wizard/step/1", {
            'password': "123456",
            'password_validation': "123456",
            # do not send 'set_system_pw'
        }).follow()
        assert_equal(good_input.status_int, 200)
        assert_equal(good_input.request.path, "//wizard/step/2")

    def test_step_2(self):
        pass  # self._test_wizard_step(2)

    def test_step_3(self):
        pass  # self._test_wizard_step(3)

    def test_step_4(self):
        pass  # self._test_wizard_step(4)

    def test_step_5(self):
        pass  # self._test_wizard_step(5)

    def test_step_6(self):
        pass  # self._test_wizard_step(6)

    def test_step_7(self):
        pass  # self._test_wizard_step(7)