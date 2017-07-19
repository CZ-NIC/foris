# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2017 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

import re

from .base import BaseConfigHandler
from foris import fapi, validators, DEVICE_CUSTOMIZATION
from foris.nuci import filters
from foris.nuci.modules.uci_raw import Uci, Section, Config, Option, Value, List
from foris.form import (
    Checkbox,
    Dropdown,
    Hidden,
    Textbox,
)

from foris.utils.translators import gettext_dummy as gettext, _


class WanHandler(BaseConfigHandler):
    userfriendly_title = gettext("WAN")

    def __init__(self, *args, **kwargs):
        # Do not display "none" options for WAN protocol if hide_no_wan is True
        self.hide_no_wan = kwargs.pop("hide_no_wan", False)
        super(WanHandler, self).__init__(*args, **kwargs)
        self.wan_ifname = "eth2"
        if DEVICE_CUSTOMIZATION == "omnia":
            self.wan_ifname = "eth1"

    def get_form(self):
        # WAN
        wan_form = fapi.ForisForm(
            "wan", self.data,
            filter=filters.create_config_filter("network", "smrtd", "ucollect")
        )
        wan_main = wan_form.add_section(
            name="set_wan",
            title=_(self.userfriendly_title),
            description=_("Here you specify your WAN port settings. Usually, you can leave this "
                          "options untouched unless instructed otherwise by your internet service "
                          "provider. Also, in case there is a cable or DSL modem connecting your "
                          "router to the network, it is usually not necessary to change this "
                          "setting."))
        WAN_DHCP = "dhcp"
        WAN_STATIC = "static"
        WAN_PPPOE = "pppoe"
        WAN_OPTIONS = (
            (WAN_DHCP, _("DHCP (automatic configuration)")),
            (WAN_STATIC, _("Static IP address (manual configuration)")),
            (WAN_PPPOE, _("PPPoE (for DSL bridges, Modem Turris, etc.)")),
        )

        WAN6_NONE = "none"
        WAN6_DHCP = "dhcpv6"
        WAN6_STATIC = "static"

        WAN6_OPTIONS = (
            (WAN6_DHCP, _("DHCPv6 (automatic configuration)")),
            (WAN6_STATIC, _("Static IP address (manual configuration)")),
        )

        if not self.hide_no_wan:
            WAN6_OPTIONS = ((WAN6_NONE, _("Disable IPv6")),) + WAN6_OPTIONS

        # protocol
        wan_main.add_field(Dropdown, name="proto", label=_("IPv4 protocol"),
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

        def extract_dns_item(dns_option, index, default=None):
            if isinstance(dns_option, List):
                dns_list = [e.content for e in dns_option.children]
            elif isinstance(dns_option, Option):
                dns_list = dns_option.value.split(" ")
            else:
                return default

            # Server with higher priority should be last
            dns_list.reverse()

            try:
                return dns_list[index]
            except IndexError:
                return default

        # DNS servers
        wan_main.add_field(Textbox, name="dns1", label=_("DNS server 1"),
                           nuci_path="uci.network.wan.dns",
                           nuci_preproc=lambda val: extract_dns_item(val, 0),
                           validators=validators.AnyIP(),
                           hint=_("DNS server address is not required as the built-in "
                                  "DNS resolver is capable of working without it."))\
            .requires("proto", WAN_STATIC)
        wan_main.add_field(Textbox, name="dns2", label=_("DNS server 2"),
                           nuci_path="uci.network.wan.dns",
                           nuci_preproc=lambda val: extract_dns_item(val, 1),
                           validators=validators.AnyIP(),
                           hint=_("DNS server address is not required as the built-in "
                                  "DNS resolver is capable of working without it."))\
            .requires("proto", WAN_STATIC)

        # xDSL settings
        wan_main.add_field(Textbox, name="username", label=_("PAP/CHAP username"),
                           nuci_path="uci.network.wan.username")\
            .requires("proto", WAN_PPPOE)
        wan_main.add_field(Textbox, name="password", label=_("PAP/CHAP password"),
                           nuci_path="uci.network.wan.password")\
            .requires("proto", WAN_PPPOE)

        # IPv6 configuration
        wan_main.add_field(Dropdown, name="wan6_proto", label=_("IPv6 protocol"),
                           args=WAN6_OPTIONS, default=WAN6_NONE,
                           nuci_path="uci.network.wan6.proto")
        wan_main.add_field(Textbox, name="ip6addr", label=_("IPv6 address"),
                           nuci_path="uci.network.wan6.ip6addr",
                           validators=validators.IPv6Prefix(),
                           hint=_("IPv6 address and prefix length for WAN interface, "
                                  "e.g. 2001:db8:be13:37da::1/64"),
                           required=True)\
            .requires("wan6_proto", WAN6_STATIC)
        wan_main.add_field(Textbox, name="ip6gw", label=_("IPv6 gateway"),
                           validators=validators.IPv6(),
                           nuci_path="uci.network.wan6.ip6gw")\
            .requires("wan6_proto", WAN6_STATIC)
        wan_main.add_field(Textbox, name="ip6prefix", label=_("IPv6 prefix"),
                           validators=validators.IPv6Prefix(),
                           nuci_path="uci.network.wan6.ip6prefix",
                           hint=_("Address range for local network, "
                                  "e.g. 2001:db8:be13:37da::/64"))\
            .requires("wan6_proto", WAN6_STATIC)

        # enable SMRT settings only if smrtd config is present
        has_smrtd = wan_form.nuci_config.find_child("uci.smrtd") is not None

        if has_smrtd:
            wan_main.add_field(Hidden, name="has_smrtd", default="1")
            wan_main.add_field(Checkbox, name="use_smrt", label=_("Use Modem Turris"),
                               nuci_path="uci.smrtd.global.enabled",
                               nuci_preproc=lambda val: bool(int(val.value)),
                               hint=_("Modem Turris (aka SMRT - Small Modem for Router Turris), "
                                      "a simple ADSL/VDSL modem designed specially for router "
                                      "Turris. Enable this option if you have Modem Turris "
                                      "connected to your router."))\
                .requires("proto", WAN_PPPOE)

            def get_smrtd_param(param_name):
                """Helper function for getting SMRTd params for "connections" list."""
                def wrapped(conn_list):
                    # internet connection must be always first list element
                    vlan_id, vpi, vci = (conn_list.children[0].content.split(" ")
                                         if conn_list else (None, None, None))
                    if param_name == "VPI":
                        return vpi
                    elif param_name == "VCI":
                        return vci
                    elif param_name == "VLAN":
                        return vlan_id
                    raise ValueError("Unknown SMRTd connection parameter.")
                return wrapped

            def get_smrtd_vlan(data):
                """Helper function for getting VLAN number from Uci data."""
                ifname = data.find_child("uci.network.wan.ifname")
                if ifname:
                    ifname = ifname.value
                    matches = re.match("%s.(\d+)" % self.wan_ifname, ifname)
                    if matches:
                        return matches.group(1)

                connections = data.find_child("uci.smrtd.%s.connections" % self.wan_ifname)
                result = get_smrtd_param("VLAN")(connections)
                return result

            # 802.1Q VLAN number is 12-bit, 0x0 and 0xFFF reserved
            wan_main.add_field(Textbox, name="smrt_vlan", label=_("xDSL VLAN number"),
                               nuci_preproc=get_smrtd_vlan,
                               validators=[validators.PositiveInteger(),
                                           validators.InRange(1, 4095)],
                               hint=_("VLAN number for your internet connection. Your ISP might "
                                      "have provided you this number. If you have VPI and VCI "
                                      "numbers instead, leave this field empty, a default value "
                                      "will be used automatically."))\
                .requires("use_smrt", True)

            vpi_vci_validator = validators.RequiredWithOtherFields(
                ("smrt_vpi", "smrt_vci"),
                _("Both VPI and VCI must be filled or both must be empty.")
            )

            wan_main.add_field(
                Textbox, name="smrt_vpi", label=_("VPI"),
                nuci_path="uci.smrtd.%s.connections" % self.wan_ifname,
                nuci_preproc=get_smrtd_param("VPI"),
                validators=[validators.PositiveInteger(),
                            validators.InRange(0, 255),
                            vpi_vci_validator],
                hint=_("Virtual Path Identifier (VPI) is a parameter that you might have received "
                       "from your ISP. If you have a VLAN number instead, leave this field empty. "
                       "You need to fill in both VPI and VCI together.")
            ) \
                .requires("use_smrt", True)
            wan_main.add_field(
                Textbox, name="smrt_vci", label=_("VCI"),
                nuci_path="uci.smrtd.%s.connections" % self.wan_ifname,
                nuci_preproc=get_smrtd_param("VCI"),
                validators=[validators.PositiveInteger(),
                            validators.InRange(32, 65535),
                            vpi_vci_validator],
                hint=_("Virtual Circuit Identifier (VCI) is a parameter that you might have "
                       "received from your ISP. If you have a VLAN number instead, leave this "
                       "field empty. You need to fill in both VPI and VCI together.")
            )\
                .requires("use_smrt", True)

        # custom MAC
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
            network = Config("network")
            uci.add(network)

            wan = Section("wan", "interface")
            network.add(wan)

            wan.add(Option("proto", data['proto']))
            if data['custom_mac'] is True:
                wan.add(Option("macaddr", data['macaddr']))
            else:
                wan.add_removal(Option("macaddr", None))

            ucollect_ifname = self.wan_ifname

            if data['proto'] == WAN_PPPOE:
                wan.add(Option("username", data['username']))
                wan.add(Option("password", data['password']))
                wan.add(Option("ipv6", data.get("wan6_proto") is not WAN6_NONE))
                ucollect_ifname = "pppoe-wan"
            elif data['proto'] == WAN_STATIC:
                wan.add(Option("ipaddr", data['ipaddr']))
                wan.add(Option("netmask", data['netmask']))
                wan.add(Option("gateway", data['gateway']))
                dns_list = List("dns")
                dns2 = data.get("dns2", None)
                if dns2:
                    dns_list.add(Value(0, dns2))
                dns1 = data.get("dns1", None)
                if dns1:
                    dns_list.add(Value(1, dns1))  # dns with higher priority should be added last
                if not dns_list.children:
                    wan.add_removal(dns_list)
                else:
                    wan.add_replace(dns_list)

            # IPv6 configuration
            wan6 = Section("wan6", "interface")
            network.add(wan6)
            wan6.add(Option("ifname", "@wan"))
            wan6.add(Option("proto", data['wan6_proto']))

            if data.get("wan6_proto") == WAN6_STATIC:
                wan6.add(Option("ip6addr", data['ip6addr']))
                wan6.add(Option("ip6gw", data['ip6gw']))
                wan6.add(Option("ip6prefix", data['ip6prefix']))
            else:
                wan6.add_removal(Option("ip6addr", None))
                wan6.add_removal(Option("ip6gw", None))
                wan6.add_removal(Option("ip6prefix", None))

            if has_smrtd:
                smrtd = Config("smrtd")
                uci.add(smrtd)

                smrt_vlan = data.get("smrt_vlan")
                use_smrt = data.get("use_smrt", False)

                wan_if = Section(self.wan_ifname, "interface")
                smrtd.add(wan_if)
                wan_if.add(Option("name", self.wan_ifname))

                if use_smrt:
                    if not smrt_vlan:
                        # "proprietary" number - and also a common VLAN ID in CZ
                        smrt_vlan = "848"
                        self.wan_ifname += ".%s" % smrt_vlan

                vpi, vci = data.get("smrt_vpi"), data.get("smrt_vci")
                connections = List("connections")
                if vpi and vci:
                    wan_if.add(connections)
                    connections.add(Value(1, "%s %s %s" % (smrt_vlan, vpi, vci)))
                elif use_smrt:
                    wan_if.add_removal(connections)

                smrtd_global = Section("global", "global")
                smrtd.add(smrtd_global)
                smrtd_global.add(Option("enabled", use_smrt))

                # set correct ifname for WAN - must be changed when disabling SMRT
                wan.add(Option("ifname", self.wan_ifname))

            # set interface for ucollect to listen on
            interface_if_name = None
            ucollect_interface0 = wan_form.nuci_config.find_child("uci.ucollect.@interface[0]")
            if ucollect_interface0:
                interface_if_name = ucollect_interface0.name

            ucollect = Config("ucollect")
            uci.add(ucollect)
            interface = Section(interface_if_name, "interface", True)
            ucollect.add(interface)
            interface.add(Option("ifname", ucollect_ifname))

            return "edit_config", uci

        wan_form.add_callback(wan_form_cb)

        return wan_form
