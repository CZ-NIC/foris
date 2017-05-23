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

from foris import fapi
from foris import validators
from foris.core import gettext_dummy as gettext, ugettext as _
from foris.form import (
    Textbox, Checkbox
)
from foris.nuci import client
from foris.nuci.filters import create_config_filter, wifi_filter
from foris.nuci.preprocessors import guest_network_enabled, generate_network_preprocessor
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option, List, Value
from foris.utils.addresses import (
    ip_num_to_str_4, ip_str_to_num_4, prefix_to_mask_4, mask_to_prefix_4
)
from foris.utils.routing import reverse


from .base import BaseConfigHandler


DEFAULT_GUEST_NETWORK = "10.111.222.0"
DEFAULT_GUEST_MASK = "255.255.255.0"
DEFAULT_GUEST_PREFIX = mask_to_prefix_4(DEFAULT_GUEST_MASK)


class LanHandler(BaseConfigHandler):
    userfriendly_title = gettext("LAN")

    def get_form(self):
        lan_form = fapi.ForisForm("lan", self.data,
                                  filter=create_config_filter("dhcp", "network", "firewall"))
        lan_main = lan_form.add_section(
            name="set_lan",
            title=_(self.userfriendly_title),
            description=_("This section contains settings for the local network (LAN). The provided"
                          " defaults are suitable for most networks. <br><strong>Note:</strong> If "
                          "you change the router IP address, all computers in LAN, probably "
                          "including the one you are using now, will need to obtain a <strong>new "
                          "IP address</strong> which does <strong>not</strong> happen <strong>"
                          "immediately</strong>. It is recommended to disconnect and reconnect all "
                          "LAN cables after submitting your changes to force the update. The next "
                          "page will not load until you obtain a new IP from DHCP (if DHCP enabled)"
                          " and you might need to <strong>refresh the page</strong> in your "
                          "browser.")
        )

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

        guest_network_section = lan_form.add_section(
            name="guest_network",
            title=_("Guest network"),
        )
        guest_network_section.add_field(
            Checkbox, name="guest_network_enabled",
            label=_("Enable guest network"), default=False,
            hint=_(
                "Guest network is used for <a href='%(url)s'>guest Wi-Fi</a>. It is separated  "
                "from your ordinary LAN network. Devices connected to this network are allowed "
                "to access the internet, but are not allowed to access other devices and "
                "the configuration interface of the router."
            ) % dict(url=reverse("config_page", page_name="wifi")),
            nuci_preproc=guest_network_enabled,
        )
        guest_network_section.add_field(
            Textbox, name="guest_network_subnet", label=_("Guest network"),
            nuci_preproc=generate_network_preprocessor(
                "uci.network.guest_turris.ipaddr",
                "uci.network.guest_turris.netmask",
                DEFAULT_GUEST_NETWORK,
                DEFAULT_GUEST_MASK,
            ),
            validators=[validators.IPv4Prefix()],
            hint=_(
                "You need to set the IP range for your guest network. It is necessary that "
                "the range is different than ranges on your other networks (LAN, WAN, VPN, etc.)."
            ),
        ).requires("guest_network_enabled", True)

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

            # update guest network configs
            guest_enabled = data.get("guest_network_enabled")
            guest_network_subnet = data.get("guest_network_subnet")
            if guest_network_subnet:
                network, prefix = data.get("guest_network_subnet").split("/")
            else:
                network, prefix = DEFAULT_GUEST_NETWORK, DEFAULT_GUEST_PREFIX
            LanHandler.prepare_guest_configs(uci, guest_enabled, network, prefix)

            # disable guest wifi when guest network is not enabled
            if not guest_enabled:
                wireless = uci.add(Config("wireless"))
                data = client.get(filter=wifi_filter())
                idx = 0
                while data.find_child("uci.wireless.@wifi-device[%d]" % idx):
                    guest_iface = wireless.add(Section("guest_iface_%d" % idx, "wifi-iface"))
                    guest_iface.add(Option("disabled", "1"))
                    idx += 1

            return "edit_config", uci

        lan_form.add_callback(lan_form_cb)

        return lan_form

    @staticmethod
    def prepare_guest_configs(uci, enabled, network, prefix):
        ignore = "0" if enabled else "1"
        enabled = "1" if enabled else "0"

        # parse router ip address (192.168.1.0 -> 192.168.1.1)
        router_ip = ip_num_to_str_4(ip_str_to_num_4(network) + 1)
        netmask = prefix_to_mask_4(int(prefix))

        # update network interface list
        network_conf = uci.find_child("network") or Config("network")
        uci.add(network_conf)
        interface_section = Section("guest_turris", "interface")
        network_conf.add_replace(interface_section)
        interface_section.add(Option("enabled", enabled))
        interface_section.add(Option("ifname", "guest_turris"))
        interface_section.add(Option("proto", "static"))
        interface_section.add(Option("ipaddr", router_ip))
        interface_section.add(Option("netmask", netmask))

        # update firewall config
        firewall_conf = uci.find_child("firewall") or Config("firewall")
        uci.add(firewall_conf)

        zone_section = Section("guest_turris", "zone")
        firewall_conf.add_replace(zone_section)
        zone_section.add(Option("enabled", enabled))
        zone_section.add(Option("name", "guest_turris"))
        network_list = List("network")
        network_list.add(Value(0, "guest_turris"))
        zone_section.add(network_list)
        zone_section.add(Option("input", "REJECT"))
        zone_section.add(Option("forward", "REJECT"))
        zone_section.add(Option("output", "ACCEPT"))

        wan_forwarding_section = Section("guest_turris_forward_wan", "forwarding")
        firewall_conf.add_replace(wan_forwarding_section)
        wan_forwarding_section.add(Option("enabled", enabled))
        wan_forwarding_section.add(Option("name", "guest to wan forward"))
        wan_forwarding_section.add(Option("src", "guest_turris"))
        wan_forwarding_section.add(Option("dest", "wan"))

        dns_rule_section = Section("guest_turris_dns_rule", "rule")
        firewall_conf.add_replace(dns_rule_section)
        dns_rule_section.add(Option("enabled", enabled))
        dns_rule_section.add(Option("name", "guest dns rule"))
        dns_rule_section.add(Option("src", "guest_turris"))
        dns_rule_section.add(Option("proto", "tcpudp"))
        dns_rule_section.add(Option("dest_port", 53))
        dns_rule_section.add(Option("target", "ACCEPT"))

        dhcp_rule_section = Section("guest_turris_dhcp_rule", "rule")
        firewall_conf.add_replace(dhcp_rule_section)
        dhcp_rule_section.add(Option("enabled", enabled))
        dhcp_rule_section.add(Option("name", "guest dhcp rule"))
        dhcp_rule_section.add(Option("src", "guest_turris"))
        dhcp_rule_section.add(Option("proto", "udp"))
        dhcp_rule_section.add(Option("src_port", "67-68"))
        dhcp_rule_section.add(Option("dest_port", "67-68"))
        dhcp_rule_section.add(Option("target", "ACCEPT"))

        # update dhcp config
        dhcp_conf = uci.find_child("dhcp") or Config("dhcp")
        uci.add(dhcp_conf)

        dhcp_section = Section("guest_turris", "dhcp")
        dhcp_conf.add(dhcp_section)
        dhcp_section.add(Option("interface", "guest_turris"))
        dhcp_section.add(Option("start", "200"))
        dhcp_section.add(Option("limit", "50"))
        dhcp_section.add(Option("leasetime", "1h"))
        dhcp_section.add(Option("ignore", ignore))
        dhcp_option_list = List("dhcp_option")
        dhcp_option_list.add(Value(0, "6,%s" % router_ip))
        dhcp_section.add(dhcp_option_list)
