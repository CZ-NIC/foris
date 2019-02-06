# coding=utf-8

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

from foris import fapi, validators
from foris.form import Textbox, Checkbox, Dropdown, Number
from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, _


from .base import BaseConfigHandler

import ipaddress


class LanHandler(BaseConfigHandler):
    userfriendly_title = gettext("LAN")

    def __init__(self, *args, **kwargs):
        super(LanHandler, self).__init__(*args, **kwargs)
        self.backend_data = current_state.backend.perform("lan", "get_settings")

    def get_form(self):
        data = {}
        data["mode"] = self.backend_data["mode"]
        data["router_ip"] = self.backend_data["mode_managed"]["router_ip"]
        data["router_netmask"] = self.backend_data["mode_managed"]["netmask"]
        data["router_dhcp_enabled"] = self.backend_data["mode_managed"]["dhcp"]["enabled"]
        data["router_dhcp_start"] = self.backend_data["mode_managed"]["dhcp"]["start"]
        data["router_dhcp_limit"] = self.backend_data["mode_managed"]["dhcp"]["limit"]
        data["router_dhcp_leasetime"] = self.backend_data["mode_managed"]["dhcp"]["lease_time"] \
            // (60 * 60)
        data["client_proto_4"] = self.backend_data["mode_unmanaged"]["lan_type"]
        data["client_ip_4"] = self.backend_data["mode_unmanaged"]["lan_static"]["ip"]
        data["client_netmask_4"] = self.backend_data["mode_unmanaged"]["lan_static"]["netmask"]
        data["client_gateway_4"] = self.backend_data["mode_unmanaged"]["lan_static"]["gateway"]
        dns1 = self.backend_data["mode_unmanaged"]["lan_static"].get("dns1")
        if dns1:
            data["client_dns1_4"] = dns1
        dns2 = self.backend_data["mode_unmanaged"]["lan_static"].get("dns2")
        if dns2:
            data["client_dns2_4"] = dns2
        data["client_hostname_4"] = self.backend_data["mode_unmanaged"]["lan_dhcp"].get(
            "hostname", "")

        if self.data:
            # Update from post
            data.update(self.data)

        lan_form = fapi.ForisForm("lan", data, validators=[
            validators.DhcpRangeValidator(
                'router_netmask', 'router_dhcp_start', 'router_dhcp_limit',
                gettext(
                    "<strong>DHCP start</strong> and <strong>DHCP max leases</strong> "
                    "does not fit into <strong>Network netmask</strong>!"
                ),
                [
                    lambda data: data['mode'] != 'managed',
                    lambda data: not data['router_dhcp_enabled'],
                ]
            )
        ])
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

        lan_main.add_field(
            Dropdown, name="mode", label=_("LAN mode"), args=[
                ("managed", _("Router")),
                ("unmanaged", _("Computer")),
            ],
            hint=_(
                "Router mode means that this devices manages the LAN "
                "(acts as a router, can assing IP addresses, ...). "
                "Computer mode means that this device acts as a client in this network. "
                "It acts in a similar way as WAN, but it has opened ports for configuration "
                "interface and other services."
            ),
            default="managed",
        )

        # managed options
        lan_main.add_field(
            Textbox, name="router_ip", label=_("Router IP address"),
            validators=validators.IPv4(),
            hint=_("Router's IP address in the inner network.")
        ).requires("mode", "managed")
        lan_main.add_field(
            Textbox, name="router_netmask", label=_("Network netmask"),
            validators=validators.IPv4Netmask(),
            hint=_("Network mask of the inner network.")
        ).requires("mode", "managed")
        lan_main.add_field(
            Checkbox, name="router_dhcp_enabled", label=_("Enable DHCP"),
            preproc=lambda val: bool(int(val)), default=True,
            hint=_("Enable this option to automatically assign IP addresses to "
                   "the devices connected to the router.")
        ).requires("mode", "managed")
        lan_main.add_field(
            Number, name="router_dhcp_start", label=_("DHCP start"),
        ).requires("router_dhcp_enabled", True)
        lan_main.add_field(
            Number, name="router_dhcp_limit", label=_("DHCP max leases"),
        ).requires("router_dhcp_enabled", True)
        lan_main.add_field(
            Number, name="router_dhcp_leasetime", label=_("Lease time (hours)"),
            validators=[validators.InRange(1, 7 * 24)]
        ).requires("router_dhcp_enabled", True)

        # unmanaged options
        LAN_DHCP = "dhcp"
        LAN_STATIC = "static"
        LAN_NONE = "none"
        LAN_OPTIONS = (
            (LAN_DHCP, _("DHCP (automatic configuration)")),
            (LAN_STATIC, _("Static IP address (manual configuration)")),
            (LAN_NONE, _("Don't connect this device to LAN")),
        )
        lan_main.add_field(
            Dropdown, name="client_proto_4", label=_("IPv4 protocol"), args=LAN_OPTIONS,
            default=LAN_DHCP
        ).requires("mode", "unmanaged")
        # unmanaged static
        lan_main.add_field(
            Textbox, name="client_ip_4", label=_("IPv4 address"), required=True,
            validators=validators.IPv4()
        ).requires("client_proto_4", LAN_STATIC)
        lan_main.add_field(
            Textbox, name="client_netmask_4", label=_("Network mask"), required=True,
            validators=validators.IPv4Netmask()
        ).requires("client_proto_4", LAN_STATIC)
        lan_main.add_field(
            Textbox, name="client_gateway_4", label=_("Gateway"), required=True,
            validators=validators.IPv4(),
        ).requires("client_proto_4", LAN_STATIC)
        lan_main.add_field(
            Textbox, name="client_dns1_4", label=_("DNS server 1 (IPv4)"),
            validators=validators.IPv4(),
            hint=_(
                "DNS server address is not required as the built-in "
                "DNS resolver is capable of working without it."
            )
        ).requires("client_proto_4", LAN_STATIC)
        lan_main.add_field(
            Textbox, name="client_dns2_4", label=_("DNS server 2 (IPv4)"),
            validators=validators.IPv4(),
            hint=_(
                "DNS server address is not required as the built-in "
                "DNS resolver is capable of working without it."
            )
        ).requires("client_proto_4", LAN_STATIC)
        # unamanaged dhcp
        lan_main.add_field(
            Textbox, name="client_hostname_4", label=_("DHCP hostname"),
            validators=validators.Domain(),
            hint=_(
                "Hostname which will be provided to DHCP server."
            )
        ).requires("client_proto_4", LAN_DHCP)

        def lan_form_cb(data):
            msg = {"mode": data["mode"]}
            if msg["mode"] == "managed":
                dhcp = {
                    "enabled": data["router_dhcp_enabled"],
                }
                if dhcp["enabled"]:
                    dhcp["start"] = int(data["router_dhcp_start"])
                    dhcp["limit"] = int(data["router_dhcp_limit"])
                    dhcp["lease_time"] = int(data.get("router_dhcp_leasetime", 12)) * 60 * 60
                msg["mode_managed"] = {
                    "router_ip": data["router_ip"],
                    "netmask": data["router_netmask"],
                    "dhcp": dhcp,
                }
            elif data["mode"] == "unmanaged":
                msg["mode_unmanaged"] = {
                    "lan_type": data["client_proto_4"],
                }
                if data["client_proto_4"] == "static":
                    msg["mode_unmanaged"]["lan_static"] = {
                        "ip": data["client_ip_4"],
                        "netmask": data["client_netmask_4"],
                        "gateway": data["client_gateway_4"],
                    }
                    dns1 = data.get("client_dns1_4")
                    if dns1:
                        msg["mode_unmanaged"]["lan_static"]["dns1"] = dns1

                    dns2 = data.get("client_dns2_4")
                    if dns2:
                        msg["mode_unmanaged"]["lan_static"]["dns2"] = dns2

                elif data["client_proto_4"] == "dhcp":
                    hostname = data.get("client_hostname_4")
                    msg["mode_unmanaged"]["lan_dhcp"] = {"hostname": hostname} if hostname else {}

            res = current_state.backend.perform("lan", "update_settings", msg)
            return "save_result", res  # store {"result": ...} to be used later...

        lan_form.add_callback(lan_form_cb)

        return lan_form
