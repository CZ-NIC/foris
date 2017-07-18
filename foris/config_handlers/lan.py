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
from foris.form import Textbox, Checkbox, Number
from foris.nuci import client
from foris.nuci.filters import create_config_filter, wifi_filter
from foris.nuci.preprocessors import guest_network_enabled, generate_network_preprocessor
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option, List, Value, parse_uci_bool
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, _


from .base import (
    prepare_guest_configs,
    BaseConfigHandler, DEFAULT_GUEST_MASK, DEFAULT_GUEST_NETWORK, DEFAULT_GUEST_PREFIX
)


class LanHandler(BaseConfigHandler):
    userfriendly_title = gettext("LAN")

    def get_form(self):
        lan_form = fapi.ForisForm(
            "lan", self.data, filter=create_config_filter("dhcp", "network", "firewall", "sqm"))
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
        guest_network_section.add_field(
            Checkbox, name="guest_network_shapping", label=_("QoS"),
            nuci_preproc=parse_uci_bool,
            nuci_path="uci.sqm.guest_limit_turris.enabled",
            hint=_(
                "You can limit the speed of your guest network to make sure that you have "
                "enough bandwidth for your regular network.",
            ),
        ).requires("guest_network_enabled", True)
        guest_network_section.add_field(
            Number,
            name="guest_network_download", label=_("Download (kb/s)"),
            validators=[validators.PositiveInteger()],
            hint=_(
                "Upload speed in guest network (in kilobits per second)."
            ),
            default=1024,
            nuci_path="uci.sqm.guest_limit_turris.upload",
        ).requires("guest_network_shapping", True)
        guest_network_section.add_field(
            Number,
            name="guest_network_upload", label=_("Upload (kb/s)"),
            validators=[validators.PositiveInteger()],
            hint=_(
                "Download speed in guest network (in kilobits per second)."
            ),
            default=1024,
            nuci_path="uci.sqm.guest_limit_turris.download",
        ).requires("guest_network_shapping", True)

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

            # qos data
            qos = {'enabled': False}
            if 'guest_network_shapping' in data and data['guest_network_shapping']:
                qos['enabled'] = True
                qos['download'] = data['guest_network_download']
                qos['upload'] = data['guest_network_upload']

            # update guest network configs
            guest_enabled = data.get("guest_network_enabled")
            guest_network_subnet = data.get("guest_network_subnet")
            if guest_network_subnet:
                network, prefix = data.get("guest_network_subnet").split("/")
            else:
                network, prefix = DEFAULT_GUEST_NETWORK, DEFAULT_GUEST_PREFIX

            # disable guest wifi when guest network is not enabled
            data = client.get(filter=wifi_filter())
            card_count = 0
            while data.find_child("uci.wireless.@wifi-device[%d]" % card_count):
                card_count += 1
            if not guest_enabled and card_count > 0:
                wireless = uci.add(Config("wireless"))
                for i in range(card_count):
                    guest_iface = wireless.add(Section("guest_iface_%d" % i, "wifi-iface"))
                    guest_iface.add(Option("disabled", "1"))

            guest_interfaces = ["guest_turris_%d" % e for e in range(card_count)]

            prepare_guest_configs(
                uci, guest_enabled, network, prefix, guest_interfaces, qos)

            return "edit_config", uci

        lan_form.add_callback(lan_form_cb)

        return lan_form
