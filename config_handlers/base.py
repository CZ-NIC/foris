# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import logging

import bottle

from foris import ugettext as _
from form import File, Password, Textbox, Dropdown, Checkbox, Hidden, Radio, Number, Email, Time
import fapi
from nuci import client, filters
from nuci.modules.uci_raw import Uci, Config, Section, Option, List, Value
import validators


logger = logging.getLogger(__name__)


class BaseConfigHandler(object):
    def __init__(self, data=None):
        self.data = data
        self.__form_cache = None

    @property
    def form(self):
        if self.__form_cache is None:
            self.__form_cache = self.get_form()
        return self.__form_cache

    def call_action(self, action):
        """Call config page action.

        :param action:
        :return: object that can be passed as HTTP response to Bottle
        """
        raise NotImplementedError()

    def call_ajax_action(self, action):
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

    def save(self, extra_callbacks=None):
        """

        :param extra_callbacks: list of extra callbacks to call when saved
        :return:
        """
        form = self.form
        form.validate()
        if extra_callbacks:
            for cb in extra_callbacks:
                form.add_callback(cb)
        if form.valid:
            form.save()
            return True
        else:
            return False


class PasswordHandler(BaseConfigHandler):
    """
    Setting the password
    """

    # {{ _("Password") }} - for translation
    userfriendly_title = "Password"

    def __init__(self, *args, **kwargs):
        self.change = kwargs.pop("change", False)
        super(PasswordHandler, self).__init__(*args, **kwargs)

    def get_form(self):
        # form definitions
        pw_form = fapi.ForisForm("password", self.data)
        pw_main = pw_form.add_section(name="set_password", title=_(self.userfriendly_title),
                                      description=_("Set your password for this administration interface."
                                                    " The password must be at least 6 characters long."))
        if self.change:
            pw_main.add_field(Password, name="old_password", label=_("Current password"))
            label_pass1 = _("New password")
            label_pass2 = _("New password (repeat)")
        else:
            label_pass1 = _("Password")
            label_pass2 = _("Password (repeat)")
        
        pw_main.add_field(Password, name="password", label=label_pass1, required=True,
                          validators=validators.LenRange(6, 128))
        pw_main.add_field(Password, name="password_validation", label=label_pass2,
                          required=True, validators=validators.EqualTo("password", "password_validation",
                                                                       _("Passwords are not equal.")))
        pw_main.add_field(Checkbox, name="set_system_pw", label=_("Use the same password for advanced configuration"),
                          hint=_("Same password would be used for accessing this administration "
                                 "interface, for root user in LuCI web interface and for SSH login. "
                                 "Use a strong password! (If you choose not to set the password "
                                 "for advanced configuration here, you will have the option to do "
                                 "so later. Until then, the root account will be blocked.)"))

        def pw_form_cb(data):
            from beaker.crypto import pbkdf2
            if self.change:
                # if changing password, check the old pw is right first
                uci_data = client.get(filter=filters.uci)
                password_hash = uci_data.find_child("uci.foris.auth.password")
                # allow changing the password if password_hash is empty
                if password_hash:
                    password_hash = password_hash.value
                    # crypt automatically extracts salt and iterations from formatted pw hash
                    if password_hash != pbkdf2.crypt(data['old_password'], salt=password_hash):
                        return "save_result", {'wrong_old_password': True}

            uci = Uci()
            foris = Config("foris")
            uci.add(foris)
            auth = Section("auth", "config")
            foris.add(auth)
            # use 48bit pseudo-random salt internally generated by pbkdf2
            new_password_hash = pbkdf2.crypt(data['password'], iterations=1000)
            auth.add(Option("password", new_password_hash))

            if data['set_system_pw'] is True:
                client.set_password("root", data['password'])

            return "edit_config", uci

        pw_form.add_callback(pw_form_cb)
        return pw_form


class WanHandler(BaseConfigHandler):
    # {{ _("WAN") }} - for translation
    userfriendly_title = "WAN"

    def get_form(self):
        # WAN
        wan_form = fapi.ForisForm("wan", self.data, filter=filters.uci)
        wan_main = wan_form.add_section(name="set_wan", title=_(self.userfriendly_title),
                                        description=_("Here you specify your WAN port settings. "
                "Usually, you can leave this options untouched unless instructed otherwise by your "
                "internet service provider. Also, in case there is a cable or DSL modem connecting "
                "your router to the network, it is usually not necessary to change this setting."))

        WAN_DHCP = "dhcp"
        WAN_STATIC = "static"
        WAN_PPPOE = "pppoe"
        WAN_OPTIONS = (
            (WAN_DHCP, _("DHCP (automatic configuration)")),
            (WAN_STATIC, _("Static IP address (manual configuration)")),
            (WAN_PPPOE, _("PPPoE (for DSL bridges, etc.)")),
        )

        # protocol
        wan_main.add_field(Dropdown, name="proto", label=_("Protocol"),
                           nuci_path="uci.network.wan.proto",
                           args=WAN_OPTIONS, default=WAN_DHCP)

        # static ipv4
        wan_main.add_field(Textbox, name="ipaddr", label=_("IP address"),
                           nuci_path="uci.network.wan.ipaddr",
                           required=True, validators=validators.IPv4())\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="netmask", label=_("Network mask"),
                           nuci_path="uci.network.wan.netmask",
                           required=True, validators=validators.IPv4Netmask())\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="gateway", label=_("Gateway"),
                           nuci_path="uci.network.wan.gateway",
                           validators=validators.IPv4(),
                           required=True)\
            .requires("proto", WAN_STATIC)

        def extract_dns_item(dns_string, index, default=None):
            try:
                return dns_string.split(" ")[index]
            except IndexError:
                return default

        wan_main.add_field(Textbox, name="dns1", label=_("DNS server 1"),
                           nuci_path="uci.network.wan.dns",
                           nuci_preproc=lambda val: extract_dns_item(val.value, 0),
                           validators=validators.AnyIP(),
                           hint=_("DNS server address is not required as the built-in "
                                  "DNS resolver is capable of working without it."))\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="dns2", label=_("DNS server 2"),
                           nuci_path="uci.network.wan.dns",
                           nuci_preproc=lambda val: extract_dns_item(val.value, 1),
                           validators=validators.AnyIP(),
                           hint=_("DNS server address is not required as the built-in "
                                  "DNS resolver is capable of working without it."))\
            .requires("proto", WAN_STATIC)

        # static ipv6
        wan_main.add_field(Checkbox, name="static_ipv6", label=_("Use IPv6"),
                           nuci_path="uci.network.wan.ip6addr",
                           nuci_preproc=lambda val: bool(val.value))\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="ip6addr", label=_("IPv6 address"),
                           nuci_path="uci.network.wan.ip6addr",
                           validators=validators.IPv6Prefix(),
                           hint=_("IPv6 address and prefix length for WAN interface, e.g. 2001:db8:be13:37da::1/64"),
                           required=True)\
            .requires("proto", WAN_STATIC)\
            .requires("static_ipv6", True)
        wan_main.add_field(Textbox, name="ip6gw", label=_("IPv6 gateway"),
                           validators=validators.IPv6(),
                           nuci_path="uci.network.wan.ip6gw")\
            .requires("proto", WAN_STATIC)\
            .requires("static_ipv6", True)
        wan_main.add_field(Textbox, name="ip6prefix", label=_("IPv6 prefix"),
                           validators=validators.IPv6Prefix(),
                           nuci_path="uci.network.wan.ip6prefix",
                           hint=_("Address range for local network, e.g. 2001:db8:be13:37da::/64"))\
            .requires("proto", WAN_STATIC)\
            .requires("static_ipv6", True)

        wan_main.add_field(Textbox, name="username", label=_("PAP/CHAP username"),
                           nuci_path="uci.network.wan.username")\
            .requires("proto", WAN_PPPOE)
        wan_main.add_field(Textbox, name="password", label=_("PAP/CHAP password"),
                           nuci_path="uci.network.wan.password")\
            .requires("proto", WAN_PPPOE)
        wan_main.add_field(Checkbox, name="ppp_ipv6", label=_("Enable IPv6"),
                           nuci_path="uci.network.wan.ipv6",
                           nuci_preproc=lambda val: bool(int(val.value)))\
            .requires("proto", WAN_PPPOE)

        wan_main.add_field(Checkbox, name="custom_mac", label=_("Custom MAC address"),
                           nuci_path="uci.network.wan.macaddr",
                           nuci_preproc=lambda val: bool(val.value),
                           hint=_("Useful in cases, when a specific MAC address is required by "
                                  "your internet service provider."))

        wan_main.add_field(Textbox, name="macaddr", label=_("MAC address"),
                           nuci_path="uci.network.wan.macaddr",
                           validators=validators.MacAddress(),
                           hint=_("Separator is a colon, for example 00:11:22:33:44:55"),
                           required=True)\
            .requires("custom_mac", True)

        def wan_form_cb(data):
            uci = Uci()
            config = Config("network")
            uci.add(config)

            wan = Section("wan", "interface")
            config.add(wan)

            wan.add(Option("proto", data['proto']))
            if data['custom_mac'] is True:
                wan.add(Option("macaddr", data['macaddr']))
            else:
                wan.add_removal(Option("macaddr", None))

            ucollect_ifname = "eth2"

            if data['proto'] == WAN_PPPOE:
                wan.add(Option("username", data['username']))
                wan.add(Option("password", data['password']))
                wan.add(Option("ipv6", data['ppp_ipv6']))
                ucollect_ifname = "pppoe-wan"
            elif data['proto'] == WAN_STATIC:
                wan.add(Option("ipaddr", data['ipaddr']))
                wan.add(Option("netmask", data['netmask']))
                wan.add(Option("gateway", data['gateway']))
                dns_string = " ".join([data.get("dns1", ""), data.get("dns2", "")]).strip()
                wan.add(Option("dns", dns_string))
                if data.get("static_ipv6") is True:
                    wan.add(Option("ip6addr", data['ip6addr']))
                    wan.add(Option("ip6gw", data['ip6gw']))
                    wan.add(Option("ip6prefix", data['ip6prefix']))
                else:
                    wan.add_removal(Option("ip6addr", None))
                    wan.add_removal(Option("ip6gw", None))
                    wan.add_removal(Option("ip6prefix", None))

            # set interface for ucollect to listen on
            ucollect = Config("ucollect")
            # FIXME: replacing whole config is... an ugly work-around
            uci.add_replace(ucollect)
            interface = Section(None, "interface", True)
            ucollect.add(interface)
            interface.add(Option("ifname", ucollect_ifname))

            return "edit_config", uci

        wan_form.add_callback(wan_form_cb)

        return wan_form


class DNSHandler(BaseConfigHandler):
    """
    DNS-related settings, currently for enabling/disabling upstream forwarding
    """

    # {{ _("DNS") }} - for translation
    userfriendly_title = "DNS"

    def get_form(self):
        dns_form = fapi.ForisForm("dns", self.data)
        dns_main = dns_form.add_section(name="set_dns",
                                        title=_(self.userfriendly_title))
        dns_main.add_field(Checkbox, name="forward_upstream", label=_("Use forwarding"),
                           nuci_path="uci.unbound.server.forward_upstream",
                           nuci_preproc=lambda val: bool(int(val.value)), default=True)

        def dns_form_cb(data):
            uci = Uci()
            unbound = Config("unbound")
            uci.add(unbound)
            server = Section("server", "unbound")
            unbound.add(server)
            server.add(Option("forward_upstream", data['forward_upstream']))
            return "edit_config", uci

        dns_form.add_callback(dns_form_cb)
        return dns_form


class TimeHandler(BaseConfigHandler):
    # {{ _("Time") }} - for translation
    userfriendly_title = "Time"

    def _action_ntp_update(self):
        return client.ntp_update()

    def call_ajax_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        if action == "ntp_update":
            ntp_ok = self._action_ntp_update()
            return dict(success=ntp_ok)
        elif action == "time_form":
            if hasattr(self, 'render') and callable(self.render):
                # only if the subclass implements render
                return dict(success=True, form=self.render(is_xhr=True))
        raise ValueError("Unknown Wizard action.")

    def get_form(self):
        time_form = fapi.ForisForm("time", self.data, filter=filters.time)
        time_main = time_form.add_section(name="set_time", title=_(self.userfriendly_title),
                                          description=_(
            "We could not synchronize the time with a timeserver, probably due to a loss of connection. "
            "It is necessary for the router to have correct time in order to function properly. Please, "
            "synchronize it with your computer's time, or set it manually."
            ))

        time_main.add_field(Textbox, name="time", label=_("Time"), nuci_path="time",
                            nuci_preproc=lambda v: v.local)

        def time_form_cb(data):
            client.set_time(data['time'])
            return "none", None

        time_form.add_callback(time_form_cb)

        return time_form


class LanHandler(BaseConfigHandler):
    # {{ _("LAN") }} - for translation
    userfriendly_title = "LAN"
    
    def get_form(self):
        lan_form = fapi.ForisForm("lan", self.data, filter=filters.uci)
        lan_main = lan_form.add_section(name="set_lan", title=_(self.userfriendly_title),
                                        description=_("This section contains settings for the local network (LAN). "
            "The provided defaults are suitable for most networks. "
            "<br><strong>Note:</strong> If you change the router IP address, all computers in LAN, probably including the one you "
            "are using now, will need to obtain a <strong>new IP address</strong> which does <strong>not</strong> happen <strong>immediately</strong>. "
            "It is recommended to disconnect and reconnect all LAN cables after submitting your changes "
            "to force the update. The next page will not load until you obtain a new IP from DHCP "
            "(if DHCP enabled) and you might need to <strong>refresh the page</strong> in your browser."))

        lan_main.add_field(Textbox, name="lan_ipaddr", label=_("Router IP address"),
                           nuci_path="uci.network.lan.ipaddr",
                           validators=validators.IPv4(),
                           hint=_("Router's IP address in inner network. Also defines the range of "
                                  "assigned IP addresses."))
        lan_main.add_field(Checkbox, name="dhcp_enabled", label=_("Enable DHCP"),
                           nuci_path="uci.dhcp.lan.ignore",
                           nuci_preproc=lambda val: not bool(int(val.value)), default=True,
                           hint=_("Enable this option to automatically assign IP addresses to "
                                  "the devices connected to the router."))
        lan_main.add_field(Textbox, name="dhcp_min", label=_("DHCP start"),
                           nuci_path="uci.dhcp.lan.start")\
            .requires("dhcp_enabled", True)
        lan_main.add_field(Textbox, name="dhcp_max", label=_("DHCP max leases"),
                           nuci_path="uci.dhcp.lan.limit")\
            .requires("dhcp_enabled", True)

        def lan_form_cb(data):
            uci = Uci()
            config = Config("dhcp")
            uci.add(config)

            dhcp = Section("lan", "dhcp")
            config.add(dhcp)
            # FIXME: this would overwrite any unrelated DHCP options the user might have set.
            # Maybe we should get the current values, scan them and remove selectively the ones
            # with 6 in front of them? Or have some support for higher level of stuff in nuci.
            options = List("dhcp_option")
            options.add(Value(0, "6," + data['lan_ipaddr']))
            dhcp.add_replace(options)
            network = Config("network")
            uci.add(network)
            interface = Section("lan", "interface")
            network.add(interface)
            interface.add(Option("ipaddr", data['lan_ipaddr']))
            if data['dhcp_enabled']:
                dhcp.add(Option("ignore", "0"))
                dhcp.add(Option("start", data['dhcp_min']))
                dhcp.add(Option("limit", data['dhcp_max']))
            else:
                dhcp.add(Option("ignore", "1"))

            return "edit_config", uci

        lan_form.add_callback(lan_form_cb)

        return lan_form


class WifiHandler(BaseConfigHandler):
    # {{ _("Wi-Fi") }} - for translation
    userfriendly_title = "Wi-Fi"
    
    def get_form(self):
        stats = client.get(filter=filters.stats).find_child("stats")
        if len(stats.data['wireless-cards']) < 1:
            return None

        wifi_form = fapi.ForisForm("wifi", self.data, filter=filters.uci)
        wifi_main = wifi_form.add_section(name="set_wifi", title=_(self.userfriendly_title),
                                          description=_(
            "If you want to use your router as a Wi-Fi access point, enable Wi-Fi here and "
            "fill in an SSID (the name of the access point) and a corresponding password. "
            "You can then set up your mobile devices, using the QR code available next to the form."))
        wifi_main.add_field(Hidden, name="iface_section", nuci_path="uci.wireless.@wifi-iface[0]",
                            nuci_preproc=lambda val: val.name)
        wifi_main.add_field(Checkbox, name="wifi_enabled", label=_("Enable Wi-Fi"), default=True,
                            nuci_path="uci.wireless.@wifi-iface[0].disabled",
                            nuci_preproc=lambda val: not bool(int(val.value)))
        wifi_main.add_field(Textbox, name="ssid", label=_("SSID"),
                            nuci_path="uci.wireless.@wifi-iface[0].ssid",
                            required=True, validators=validators.ByteLenRange(1, 32))\
            .requires("wifi_enabled", True)
        wifi_main.add_field(Checkbox, name="ssid_hidden", label=_("Hide SSID"), default=False,
                            nuci_path="uci.wireless.@wifi-iface[0].hidden",
                            hint=_("If set, network is not visible when scanning for available networks."))\
            .requires("wifi_enabled", True)

        channels_2g4 = [("auto", _("auto"))]
        channels_5g = []
        for channel in stats.data['wireless-cards'][0]['channels']:
            if channel['disabled'] or channel['radar']:
                continue
            pretty_channel = "%s (%s MHz)" % (channel['number'], channel['frequency'])
            if channel['frequency'] < 2500:
                channels_2g4.append((str(channel['number']), pretty_channel))
            else:
                channels_5g.append((str(channel['number']), pretty_channel))

        is_dual_band = False
        # hwmode choice for dual band devices
        if len(channels_2g4) > 1 and len(channels_5g) > 1:
            is_dual_band = True
            wifi_main.add_field(Radio, name="hwmode", label=_("Wi-Fi mode"), default="11ng",
                                args=(("11ng", "2.4 GHz (g+n)"), ("11na", "5 GHz (a+n)")),
                                nuci_path="uci.wireless.radio0.hwmode",
                                hint=_("The 2.4 GHz band is more widely supported by clients, but tends to have "
                                       "more interference. The 5 GHz band is a newer standard and may not be "
                                       "supported by all your devices. It usually has less interference, "
                                       "but the signal does not carry so well indoors."))\
                .requires("wifi_enabled", True)
        # 2.4 GHz channels
        if len(channels_2g4) > 1:
            field_2g4 = wifi_main.add_field(Dropdown, name="channel2g4", label=_("Network channel"),
                                            default=channels_2g4[0][0], args=channels_2g4,
                                            nuci_path="uci.wireless.radio0.channel")
            if is_dual_band:
                field_2g4.requires("hwmode", "11ng")
        # 5 GHz channels
        if len(channels_5g) > 1:
            field_5g = wifi_main.add_field(Dropdown, name="channel5g", label=_("Network channel"),
                                           default=channels_5g[0][0], args=channels_5g,
                                           nuci_path="uci.wireless.radio0.channel")
            if is_dual_band:
                field_5g.requires("hwmode", "11na")
        wifi_main.add_field(Password, name="key", label=_("Network password"),
                            nuci_path="uci.wireless.@wifi-iface[0].key",
                            required=True,
                            validators=validators.ByteLenRange(8, 63),
                            hint=_("WPA2 pre-shared key, that is required to connect to the network. "
                                   "Minimum length is 8 characters."))\
            .requires("wifi_enabled", True)

        def wifi_form_cb(data):
            uci = Uci()
            wireless = Config("wireless")
            uci.add(wireless)

            iface = Section(data['iface_section'], "wifi-iface")
            wireless.add(iface)
            device = Section("radio0", "wifi-device")
            wireless.add(device)
            # we must toggle both wifi-iface and device
            iface.add(Option("disabled", not data['wifi_enabled']))
            device.add(Option("disabled", not data['wifi_enabled']))
            if data['wifi_enabled']:
                iface.add(Option("ssid", data['ssid']))
                iface.add(Option("hidden", data['ssid_hidden']))
                iface.add(Option("encryption", "psk2+tkip+aes"))
                iface.add(Option("key", data['key']))
                if data.get('channel2g4'):
                    channel = data['channel2g4']
                elif data.get('channel5g'):
                    channel = data['channel5g']
                else:
                    logger.critical("Saving form without Wi-Fi channel: %s" % data)
                    channel = "auto"
                hwmode = data.get('hwmode')
                if hwmode:
                    # change hwmode only if we had the choice
                    device.add(Option("hwmode", hwmode))
                # channel is in wifi-device section
                device.add(Option("channel", channel))
            else:
                pass  # wifi disabled

            return "edit_config", uci

        wifi_form.add_callback(wifi_form_cb)

        return wifi_form


class SystemPasswordHandler(BaseConfigHandler):
    """
    Setting the password of a system user (currently only root's pw).
    """
    
    # {{ _("Advanced administration") }} - for translation
    userfriendly_title = "Advanced administration"
    
    def get_form(self):
        system_pw_form = fapi.ForisForm("system_password", self.data)
        system_pw_main = system_pw_form.add_section(name="set_password",
                                                    title=_(self.userfriendly_title),
                                                    description=_(
            "In order to access the advanced configuration possibilities which are not present "
            "here, you must set the root user's password. The advanced configuration options can "
            "be managed either through the <a href=\"//%(host)s/%(path)s\">LuCI web interface"
            "</a> or over SSH.") % {'host': bottle.request.get_header('host'), 'path': 'cgi-bin/luci'})
        system_pw_main.add_field(Password, name="password", label=_("Password"), required=True,
                                 validators=validators.LenRange(6, 128))
        system_pw_main.add_field(Password, name="password_validation", label=_("Password (repeat)"),
                                 required=True, validators=validators.EqualTo("password", "password_validation",
                                                                              _("Passwords are not equal.")))

        def system_pw_form_cb(data):
            client.set_password("root", data["password"])
            return "none", None

        system_pw_form.add_callback(system_pw_form_cb)
        return system_pw_form


class MaintenanceHandler(BaseConfigHandler):
    # {{ _("Maintenance") }} - for translation
    userfriendly_title = "Maintenance"

    def get_form(self):
        maintenance_form = fapi.ForisForm("maintenance", self.data)
        maintenance_main = maintenance_form.add_section(name="restore_backup",
                                                        title=_(self.userfriendly_title))
        maintenance_main.add_field(File, name="backup_file", label=_("Backup file"), required=True)

        def maintenance_form_cb(data):
            result = client.load_config_backup(data['backup_file'].file)
            return "save_result", {'new_ip': result}

        maintenance_form.add_callback(maintenance_form_cb)
        return maintenance_form


class NotificationsHandler(BaseConfigHandler):
    # {{ _("Notifications") }} - for translation
    userfriendly_title = "Notifications"

    def get_form(self):
        notifications_form = fapi.ForisForm("notifications", self.data)

        notifications = notifications_form.add_section(name="notifications",
                                                       title=_("Notifications settings"))
        # notifications settings
        notifications.add_field(Checkbox, name="enable_smtp", label=_("Enable notifications"),
                                nuci_path="uci.user_notify.smtp.enable",
                                nuci_preproc=lambda val: bool(int(val.value)),
                                default=False)

        notifications.add_field(Radio, name="use_turris_smtp", label=_("SMTP provider"), default="0",
                                args=(("1", _("Turris")), ("0", _("Custom"))),
                                nuci_path="uci.user_notify.smtp.use_turris_smtp",
                                hint=_("If you set SMTP provider to \"Turris\", the servers provided to "
                                       "members of the Turris project would be used. These servers do "
                                       "not require any additional settings. If you want to set your "
                                       "own SMTP server, please select \"Custom\" and enter required settings."))\
            .requires("enable_smtp", True)

        notifications.add_field(Textbox, name="to", label=_("Recipient's email"),
                                nuci_path="uci.user_notify.smtp.to",
                                nuci_preproc=lambda x: " ".join(map(lambda value: value.content, x.children)),
                                hint=_("Email address of recipient. Separate multiple addresses by spaces."),
                                required=True)\
            .requires("enable_smtp", True)

        # sender's name for CZ.NIC SMTP only
        notifications.add_field(Textbox, name="sender_name", label=_("Sender's name"),
                                hint=_("Name of the sender - will be used as a part of the sender's email address before the \"at\" sign."),
                                nuci_path="uci.user_notify.smtp.sender_name",
                                validators=[validators.RegExp(_("Sender's name can contain only alphanumeric characters, dots and underscores."), r"^[0-9a-zA-Z_\.-]+$")],
                                required=True)\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "1")

        SEVERITY_OPTIONS = (
            (1, _("Reboot is required")),
            (2, _("Reboot or attention is required")),
            (3, _("Reboot or attention is required or update was installed")),
        )
        notifications.add_field(Dropdown, name="severity", label=_("Importance"),
                                nuci_path="uci.user_notify.notifications.severity",
                                nuci_preproc=lambda val: int(val.value),
                                args=SEVERITY_OPTIONS, default=1)\
            .requires("enable_smtp", True)
        notifications.add_field(Checkbox, name="news", label=_("Send news"),
                                hint=_("Send emails about new features."),
                                nuci_path="uci.user_notify.notifications.news",
                                nuci_preproc=lambda val: bool(int(val.value)),
                                default=False)\
            .requires("enable_smtp", True)

        # SMTP settings (custom server)
        smtp = notifications_form.add_section(name="smtp", title=_("SMTP settings"))
        smtp.add_field(Email, name="from", label=_("Sender address (From)"),
                       hint=_("This is the address notifications are send from."),
                       nuci_path="uci.user_notify.smtp.from",
                       required=True)\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")
        smtp.add_field(Textbox, name="server", label=_("Server address"),
                                nuci_path="uci.user_notify.smtp.server",
                                required=True)\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")
        smtp.add_field(Number, name="port", label=_("Server port"),
                                nuci_path="uci.user_notify.smtp.port",
                                validators=[validators.Integer()],
                                required=True)\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")

        SECURITY_OPTIONS = (
            ("none", _("None")),
            ("ssl", _("SSL/TLS")),
            ("starttls", _("STARTTLS")),
        )
        smtp.add_field(Dropdown, name="security", label=_("Security"),
                                nuci_path="uci.user_notify.smtp.security",
                                args=SECURITY_OPTIONS, default="none")\
            .requires("enable_smtp", True).requires("use_turris_smtp", "0")

        smtp.add_field(Textbox, name="username", label=_("Username"),
                       nuci_path="uci.user_notify.smtp.username")\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")
        smtp.add_field(Password, name="password", label=_("Password"),
                       nuci_path="uci.user_notify.smtp.password")\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")

        # reboot time
        reboot = notifications_form.add_section(name="reboot",
                                                title=_("Automatic restarts"))
        reboot.add_field(Number, name="delay", label=_("Delay (days)"),
                         hint=_("Number of days that must pass between receiving the request "
                                "for restart and the automatic restart itself."),
                         nuci_path="uci.user_notify.reboot.delay",
                         validators=[validators.InRange(0, 10)],
                         required=True)
        reboot.add_field(Time, name="reboot_time", label=_("Reboot time"),
                         hint=_("Time of day of automatic reboot in HH:MM format."),
                         nuci_path="uci.user_notify.reboot.time",
                         validators=[validators.Time()],
                         required=True)

        def notifications_form_cb(data):
            uci = Uci()
            user_notify = Config("user_notify")
            uci.add(user_notify)

            smtp = Section("smtp", "smtp")
            user_notify.add(smtp)
            smtp.add(Option("enable", data['enable_smtp']))
            smtp.add(Option("use_turris_smtp", data['use_turris_smtp']))

            reboot = Section("reboot", "reboot")
            user_notify.add(reboot)
            reboot.add(Option("time", data['reboot_time']))
            reboot.add(Option("delay", data['delay']))

            if data['enable_smtp']:
                if data['use_turris_smtp'] == "0":
                    smtp.add(Option("server", data['server']))
                    smtp.add(Option("port", data['port']))
                    smtp.add(Option("username", data['username']))
                    smtp.add(Option("password", data['password']))
                    smtp.add(Option("security", data['security']))
                    smtp.add(Option("from", data['from']))
                else:
                    smtp.add(Option("sender_name", data['sender_name']))
                to = List("to")
                for i, to_item in enumerate(data['to'].split(" ")):
                    if to_item:
                        to.add(Value(i, to_item))
                smtp.add_replace(to)
                # notifications section
                notifications = Section("notifications", "notifications")
                user_notify.add(notifications)
                notifications.add(Option("severity", data['severity']))
                notifications.add(Option("news", data['news']))

            return "edit_config", uci

        notifications_form.add_callback(notifications_form_cb)

        return notifications_form
