# coding=utf-8

# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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
from foris.form import Textbox, Checkbox, Number
from foris.state import current_state
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, _


from .base import BaseConfigHandler, DEFAULT_GUEST_MASK, DEFAULT_GUEST_IP


class GuestHandler(BaseConfigHandler):
    userfriendly_title = gettext("Guest network")

    def __init__(self, *args, **kwargs):
        super(GuestHandler, self).__init__(*args, **kwargs)
        self.backend_data = current_state.backend.perform("guest", "get_settings")

    def get_form(self):
        data = {}
        data["guest_enabled"] = self.backend_data["enabled"]
        data["guest_ipaddr"] = self.backend_data["ip"]
        data["guest_netmask"] = self.backend_data["netmask"]
        data["guest_dhcp_enabled"] = self.backend_data["dhcp"]["enabled"]
        data["guest_dhcp_start"] = self.backend_data["dhcp"]["start"]
        data["guest_dhcp_limit"] = self.backend_data["dhcp"]["limit"]
        data["guest_dhcp_leasetime"] = self.backend_data["dhcp"]["lease_time"] // 60 // 60
        data["guest_qos_enabled"] = self.backend_data["qos"]["enabled"]
        data["guest_qos_download"] = self.backend_data["qos"]["download"]
        data["guest_qos_upload"] = self.backend_data["qos"]["upload"]

        if self.data:
            # Update from post
            data.update(self.data)

        guest_form = fapi.ForisForm(
            "guest",
            data,
            validators=[
                validators.DhcpRangeValidator(
                    "guest_netmask",
                    "guest_dhcp_start",
                    "guest_dhcp_limit",
                    gettext(
                        "<strong>DHCP start</strong> and <strong>DHCP max leases</strong> "
                        "does not fit into <strong>Guest network netmask</strong>!"
                    ),
                    [
                        lambda data: not data.get("guest_enabled"),
                        lambda data: not data.get("guest_dhcp_enabled"),
                    ],
                ),
                validators.DhcpRangeRouterIpValidator(
                    "guest_ipaddr",
                    "guest_netmask",
                    "guest_dhcp_start",
                    "guest_dhcp_limit",
                    gettext(
                        "<strong>Router IP</strong> should not be within DHCP range "
                        "defined by <strong>DHCP start</strong> and <strong>DHCP max leases "
                        "</strong>"
                    ),
                    [
                        lambda data: not data.get("guest_dhcp_enabled"),
                        lambda data: not data.get("guest_enabled"),
                    ],
                ),
            ],
        )
        guest_network_section = guest_form.add_section(
            name="guest_network",
            title=_(self.userfriendly_title),
            description=_(
                "Guest network is used for <a href='%(url)s'>guest Wi-Fi</a>. It is separated  "
                "from your ordinary LAN. Devices connected to this network are allowed "
                "to access the internet, but are not allowed to access the configuration "
                "interface of the this device nor the devices in LAN."
            )
            % dict(url=reverse("config_page", page_name="wifi")),
        )
        guest_network_section.add_field(
            Checkbox, name="guest_enabled", label=_("Enable guest network"), default=False
        )
        guest_network_section.add_field(
            Textbox,
            name="guest_ipaddr",
            label=_("Router IP in guest network"),
            default=DEFAULT_GUEST_IP,
            validators=validators.IPv4(),
            hint=_(
                "Router's IP address in the guest network. It is necessary that "
                "the guest network IPs are different from other networks "
                "(LAN, WAN, VPN, etc.)."
            ),
        ).requires("guest_enabled", True)
        guest_network_section.add_field(
            Textbox,
            name="guest_netmask",
            label=_("Guest network netmask"),
            default=DEFAULT_GUEST_MASK,
            validators=validators.IPv4Netmask(),
            hint=_("Network mask of the guest network."),
        ).requires("guest_enabled", True)

        guest_network_section.add_field(
            Checkbox,
            name="guest_dhcp_enabled",
            label=_("Enable DHCP"),
            preproc=lambda val: bool(int(val)),
            default=True,
            hint=_(
                "Enable this option to automatically assign IP addresses to "
                "the devices connected to the router."
            ),
        ).requires("guest_enabled", True)
        guest_network_section.add_field(
            Textbox, name="guest_dhcp_start", label=_("DHCP start")
        ).requires("guest_dhcp_enabled", True)
        guest_network_section.add_field(
            Textbox, name="guest_dhcp_limit", label=_("DHCP max leases")
        ).requires("guest_dhcp_enabled", True)
        guest_network_section.add_field(
            Textbox,
            name="guest_dhcp_leasetime",
            label=_("Lease time (hours)"),
            validators=[validators.InRange(1, 7 * 24)],
        ).requires("guest_dhcp_enabled", True)

        guest_network_section.add_field(
            Checkbox,
            name="guest_qos_enabled",
            label=_("Guest Lan QoS"),
            hint=_(
                "This option enables you to set a bandwidth limit for the guest network, "
                "so that your main network doesn't get slowed-down by it."
            ),
        ).requires("guest_enabled", True)

        guest_network_section.add_field(
            Number,
            name="guest_qos_download",
            label=_("Download (kb/s)"),
            validators=[validators.PositiveInteger()],
            hint=_("Download speed in guest network (in kilobits per second)."),
            default=1024,
        ).requires("guest_qos_enabled", True)
        guest_network_section.add_field(
            Number,
            name="guest_qos_upload",
            label=_("Upload (kb/s)"),
            validators=[validators.PositiveInteger()],
            hint=_("Upload speed in guest network (in kilobits per second)."),
            default=1024,
        ).requires("guest_qos_enabled", True)

        def guest_form_cb(data):
            if data["guest_enabled"]:
                msg = {
                    "enabled": data["guest_enabled"],
                    "ip": data["guest_ipaddr"],
                    "netmask": data["guest_netmask"],
                    "dhcp": {"enabled": data["guest_dhcp_enabled"]},
                    "qos": {"enabled": data["guest_qos_enabled"]},
                }
                if data["guest_dhcp_enabled"]:
                    msg["dhcp"]["start"] = int(data["guest_dhcp_start"])
                    msg["dhcp"]["limit"] = int(data["guest_dhcp_limit"])
                    msg["dhcp"]["lease_time"] = int(data["guest_dhcp_leasetime"]) * 60 * 60

                if data["guest_qos_enabled"]:
                    msg["qos"]["download"] = int(data["guest_qos_download"])
                    msg["qos"]["upload"] = int(data["guest_qos_upload"])
            else:
                msg = {"enabled": False}

            res = current_state.backend.perform("guest", "update_settings", msg)
            return "save_result", res  # store {"result": ...} to be used later...

        guest_form.add_callback(guest_form_cb)

        return guest_form
