from bottle import Bottle, template, request
import bottle
import logging
from form import Password, Textbox, Dropdown, Checkbox, Hidden
import fapi
from nuci import client
from nuci.modules import time, uci_raw, updater
from nuci.modules.uci_raw import Uci, Config, Section, Option
from validators import LenRange
import validators
import xml.etree.cElementTree as ET


logger = logging.getLogger("wizard")

# filter later used for config filtering
uci_filter = ET.Element(uci_raw.Uci.qual_tag("uci"))
updater_filter = ET.Element(updater.Updater.qual_tag("updater"))


class BaseWizardStep(object):
    template = "wizard/form"
    name = None

    def __init__(self, data=None):
        self.data = data
        self.__form_cache = None

    @property
    def form(self):
        if self.__form_cache is None:
            self.__form_cache = self.get_form()
        return self.__form_cache

    def call_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        raise NotImplementedError()

    def get_form(self):
        """Get form for this wizard. MUST be a single-section form.

        :return:
        :rtype: fapi.ForisForm
        """
        raise NotImplementedError()

    def default_template(self, **kwargs):
        return template(self.template, stepname=self.name, **kwargs)

    def render(self, **kwargs):
        try:
            form = self.form
            # since wizard form is a single-section form...
            first_section = self.form.sections[0]
            kwargs['first_title'] = first_section.title
            kwargs['first_description'] = first_section.description
            assert "form" not in kwargs
        except NotImplementedError:
            form = None

        return self.default_template(form=form, **kwargs)

    def save(self):
        form = self.form
        form.validate()
        if form.valid:
            form.save()
            return True
        else:
            return False


class WizardStep1(BaseWizardStep):
    """
    Setting the password
    """
    name = "password"

    def get_form(self):
        # form definitions
        pw_form = fapi.ForisForm("password", self.data)
        pw_main = pw_form.add_section(name="set_password", title="Password",
                                      description="Set your password.")
        pw_main.add_field(Password, name="password", label="Password", required=True,
                          validators=LenRange(6, 60))
        pw_main.add_field(Password, name="password_validation", label="Password (repeat)")
        pw_form.add_validator(validators.FieldsEqual("password", "password_validation",
                                                      "Passwords are not equal."))

        def pw_form_cb(data):
            password = data['password']
            password = "PBKDF2:%s" % password  # TODO: PBKDF2

            uci = Uci()
            cznic = Config("cznic")
            uci.add(cznic)
            foris = Section("foris", "config")
            cznic.add(foris)
            foris.add(Option("password", password))

            return "edit_config", uci

        pw_form.add_callback(pw_form_cb)
        return pw_form


class WizardStep2(BaseWizardStep):
    """
    WAN settings.
    """
    name = "wan"

    def get_form(self):
        # WAN
        wan_form = fapi.ForisForm("wan", self.data, filter=uci_filter)
        wan_main = wan_form.add_section(name="set_wan", title="WAN")

        WAN_DHCP = "dhcp"
        WAN_STATIC = "static"
        WAN_PPPOE = "pppoe"
        WAN_OPTIONS = (
            (WAN_DHCP, "DHCP"),
            (WAN_STATIC, "Static"),
            (WAN_PPPOE, "PPPoE"),
        )

        wan_main.add_field(Textbox, name="macaddr", label="MAC address", nuci_path="uci.network.wan.macaddr", validators=validators.MacAddress())
        wan_main.add_field(Dropdown, name="proto", label="Mode", nuci_path="uci.network.wan.proto", args=WAN_OPTIONS, default=WAN_DHCP)
        wan_main.add_field(Textbox, name="ipaddr", label="IP address", nuci_path="uci.network.wan.ipaddr",
                           required=True, validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="netmask", label="Network mask", nuci_path="uci.network.wan.netmask",
                           required=True, validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="gateway", label="Gateway", nuci_path="uci.network.wan.gateway",
                           validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)

        wan_main.add_field(Textbox, name="username", label="DSL user", nuci_path="uci.network.wan.username",)\
            .requires("proto", WAN_PPPOE)
        wan_main.add_field(Textbox, name="password", label="DSL password", nuci_path="uci.network.wan.password",)\
            .requires("proto", WAN_PPPOE)

        def wan_form_cb(data):
            uci = Uci()
            config = Config("network")
            uci.add(config)

            wan = Section("wan", "interface")
            config.add(wan)
            wan.add(Option("macaddr", data['macaddr']))
            wan.add(Option("proto", data['proto']))
            if data['proto'] == WAN_PPPOE:
                wan.add(Option("username", data['username']))
                wan.add(Option("password", data['password']))
            elif data['proto'] == WAN_STATIC:
                wan.add(Option("ipaddr", data['ipaddr']))
                wan.add(Option("netmask", data['netmask']))
                wan.add(Option("gateway", data['gateway']))

            return "edit_config", uci

        wan_form.add_callback(wan_form_cb)

        return wan_form


class WizardStep3(BaseWizardStep):
    """
    Time settings.
    """
    template = "wizard/time.tpl"
    name = "time"

    def _action_ntp_update(self):
        return client.ntp_update()

    def call_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        if action == "ntp_update":
            ntp_ok = self._action_ntp_update()
            return dict(success=ntp_ok)
        elif action == "time_form":
            return dict(success=True, form=self.render(is_xhr=True))
        raise ValueError("Unknown Wizard action.")

    def get_form(self):
        time_form = fapi.ForisForm("time", self.data, filter=ET.Element(time.Time.qual_tag("time")))
        time_main = time_form.add_section(name="set_time", title="Time")

        time_main.add_field(Textbox, name="time", label="Time", nuci_path="time",
                            nuci_preproc=lambda v: v.local)

        def time_form_cb(data):
            client.set_time(data['time'])
            return "none", None

        time_form.add_callback(time_form_cb)

        return time_form

    def render(self, **kwargs):
        if kwargs.get("is_xhr"):
            assert "form" not in kwargs
            form = self.form
        else:
            form = None
        return self.default_template(form=form, **kwargs)


class WizardStep4(BaseWizardStep):
    """
    Updater.
    """
    template = "wizard/updater.tpl"
    name = "updater"

    def _action_run_updater(self):
        return client.check_updates()

    def _action_updater_status(self):
        return client.get_updater_status()

    def call_action(self, action):
        if action == "run_updater":
            run_success = self._action_run_updater()
            return dict(success=run_success)
        elif action == "updater_status":
            status, message = self._action_updater_status()
            result = dict(success=True, status=status)
            if message:
                result['message'] = message
            return result

        raise ValueError("Unknown Wizard action.")


class WizardStep5(BaseWizardStep):
    """
    LAN settings.
    """
    name = "lan"

    def get_form(self):
        # WAN
        lan_form = fapi.ForisForm("lan", self.data, filter=uci_filter)
        lan_main = lan_form.add_section(name="set_lan", title="LAN")

        lan_main.add_field(Checkbox, name="dhcp_enabled", label="Enable DHCP", nuci_path="uci.dhcp.lan.ignore",
                           nuci_preproc=lambda val: not bool(int(val.value)), default=True)
        lan_main.add_field(Textbox, name="dhcp_subnet", label="DHCP subnet", nuci_path="uci.network.lan.ipaddr")\
            .requires("dhcp_enabled", True)
        lan_main.add_field(Textbox, name="dhcp_min", label="DHCP min", nuci_path="uci.dhcp.lan.start")\
            .requires("dhcp_enabled", True)
        lan_main.add_field(Textbox, name="dhcp_max", label="DHCP max", nuci_path="uci.dhcp.lan.limit")\
            .requires("dhcp_enabled", True)

        def lan_form_cb(data):
            uci = Uci()
            config = Config("dhcp")
            uci.add(config)

            dhcp = Section("lan", "dhcp")
            config.add(dhcp)
            if data['dhcp_enabled']:
                dhcp.add(Option("ignore", "0"))
                dhcp.add(Option("start", data['dhcp_min']))
                dhcp.add(Option("limit", data['dhcp_max']))
                network = Config("network")
                uci.add(network)
                interface = Section("lan", "interface")
                network.add(interface)
                interface.add(Option("ipaddr", data['dhcp_subnet']))
            else:
                dhcp.add(Option("ignore", "1"))

            return "edit_config", uci

        lan_form.add_callback(lan_form_cb)

        return lan_form


class WizardStep6(BaseWizardStep):
    """
    WiFi settings.
    """
    name = "wifi"

    def get_form(self):
        wifi_form = fapi.ForisForm("lan", self.data, filter=uci_filter)
        wifi_main = wifi_form.add_section(name="set_wifi", title="WiFi")
        wifi_main.add_field(Hidden, name="iface_section", nuci_path="uci.wireless.@wifi-iface[1]", nuci_preproc=lambda val: val.name)
        wifi_main.add_field(Checkbox, name="wifi_enabled", label="Enable WiFi", default=True,
                            nuci_path="uci.wireless.@wifi-iface[1].disabled",
                            nuci_preproc=lambda val: not bool(int(val.value)))
        wifi_main.add_field(Textbox, name="ssid", label="Network name",
                            nuci_path="uci.wireless.@wifi-iface[1].ssid",
                            validators=validators.LenRange(1, 32))\
            .requires("wifi_enabled", True)
        wifi_main.add_field(Checkbox, name="ssid_hidden", label="Hide network name", default=False,
                            nuci_path="uci.wireless.@wifi-iface[1].hidden")\
            .requires("wifi_enabled", True)
        wifi_main.add_field(Dropdown, name="channel", label="Network channel", default="1",
                            args=((str(i), str(i)) for i in range(1, 13)),
                            nuci_path="uci.wireless.radio1.channel")\
            .requires("wifi_enabled", True)
        wifi_main.add_field(Textbox, name="key", label="Network password",
                            nuci_path="uci.wireless.@wifi-iface[1].key")\
            .requires("wifi_enabled", True)

        def wifi_form_cb(data):
            uci = Uci()
            wireless = Config("wireless")
            uci.add(wireless)

            iface = Section(data['iface_section'], "wifi-iface")
            wireless.add(iface)
            device = Section("radio1", "wifi-device")
            wireless.add(device)
            # we must toggle both wifi-iface and device
            iface.add(Option("disabled", not data['wifi_enabled']))
            device.add(Option("disabled", not data['wifi_enabled']))
            if data['wifi_enabled']:
                iface.add(Option("ssid", data['ssid']))
                iface.add(Option("hidden", data['ssid_hidden']))
                iface.add(Option("encryption", "psk2+tkip+aes"))  # TODO: find in docs
                iface.add(Option("key", data['key']))
                # channel is in wifi-device section
                device.add(Option("channel", data['channel']))
            else:
                pass  # wifi disabled

            return "edit_config", uci

        wifi_form.add_callback(wifi_form_cb)

        return wifi_form


class WizardStep7(BaseWizardStep):
    """
    Show the activation code.
    """
    template = "wizard/registration.html"

    def render(self, **kwargs):
        registration = client.get_registration()
        return self.default_template(code=registration.value, **kwargs)


app = Bottle()


def get_wizard(number):
    """WizardStep class factory.

    :param number:
    :return:
    """
    class_name = "WizardStep%s" % number
    wiz = globals()[class_name]
    if not issubclass(wiz, BaseWizardStep):
        raise bottle.HTTPError(404, "Wizard step not found: %s" % number)
    return wiz


@app.route("/step/<number:re:\d+>/ajax")
def ajax(number=1):
    action = request.GET.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    Wizard = get_wizard(number)
    wiz = Wizard()
    try:
        result = wiz.call_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown Wizard action.")


@app.route("/", name="wizard-step")
def wizard():
    bottle.redirect("/wizard/step/1")

@app.route("/step/<number:re:\d+>", name="wizard-step")
def step(number=1):
    Wizard = get_wizard(number)
    wiz = Wizard()
    return wiz.render(stepnumber=number)


@app.route("/", method="POST")
@app.route("/step/<number:re:\d+>", method="POST")
def step_post(number=1):
    Wizard = get_wizard(number)
    wiz = Wizard(request.POST)
    if request.is_xhr:
        # only update is allowed
        logger.debug("ajax request")
        request.POST.pop("update", None)
        return dict(html=wiz.render(is_xhr=True))

    if request.POST.pop("send", False):
        try:
            if wiz.save():
                bottle.redirect("/wizard/step/%s" % str(int(number) + 1))
        except TypeError:
            # raised by Validator - could happen when the form is posted with wrong fields
            pass
    return wiz.render(stepnumber=number)