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
from foris.form import Textbox, Checkbox, Number
from foris.state import current_state
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, _


from .base import BaseConfigHandler, DEFAULT_GUEST_MASK, DEFAULT_GUEST_IP


class LanHandler(BaseConfigHandler):
    userfriendly_title = gettext("LAN")

    def get_form(self):
        data = current_state.backend.perform("lan", "get_settings", {})
        data["lan_ipaddr"] = data["ip"]
        data["lan_netmask"] = data["netmask"]
        data["dhcp_enabled"] = data["dhcp"]["enabled"]
        data["dhcp_min"] = data["dhcp"]["start"]
        data["dhcp_max"] = data["dhcp"]["limit"]
        data["guest_network_enabled"] = data["guest_network"]["enabled"]
        data["guest_network_ipaddr"] = data["guest_network"]["ip"]
        data["guest_network_netmask"] = data["guest_network"]["netmask"]
        data["guest_network_qos_enabled"] = data["guest_network"]["qos"]["enabled"]
        data["guest_network_qos_download"] = data["guest_network"]["qos"]["download"]
        data["guest_network_qos_upload"] = data["guest_network"]["qos"]["upload"]

        if self.data:
            # Update from post
            data.update(self.data)

        lan_form = fapi.ForisForm("lan", data)
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
            Textbox, name="lan_ipaddr", label=_("Router IP address"),
            validators=validators.IPv4(),
            hint=_("Router's IP address in the inner network.")
        )
        lan_main.add_field(
            Textbox, name="lan_netmask", label=_("Network netmask"),
            validators=validators.IPv4Netmask(),
            hint=_("Network mask of the inner network.")
        )
        lan_main.add_field(
            Checkbox, name="dhcp_enabled", label=_("Enable DHCP"),
            preproc=lambda val: bool(int(val)), default=True,
            hint=_("Enable this option to automatically assign IP addresses to "
                   "the devices connected to the router.")
        )
        lan_main.add_field(
            Textbox, name="dhcp_min", label=_("DHCP start"),
        ).requires("dhcp_enabled", True)
        lan_main.add_field(
            Textbox, name="dhcp_max", label=_("DHCP max leases"),
        ).requires("dhcp_enabled", True)

        if current_state.app == "config":
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
            )
            guest_network_section.add_field(
                Textbox, name="guest_network_ipaddr", label=_("Router IP in guest network"),
                default=DEFAULT_GUEST_IP,
                validators=validators.IPv4(),
                hint=_(
                    "Router's IP address in the guest network. It is necessary that "
                    "the guest network IPs are different from other networks "
                    "(LAN, WAN, VPN, etc.)."
                )
            ).requires("guest_network_enabled", True)
            guest_network_section.add_field(
                Textbox, name="guest_network_netmask", label=_("Guest network netmask"),
                default=DEFAULT_GUEST_MASK,
                validators=validators.IPv4Netmask(),
                hint=_("Network mask of the guest network.")
            ).requires("guest_network_enabled", True)

            guest_network_section.add_field(
                Checkbox, name="guest_network_qos_enabled", label=_("Guest Lan QoS"),
                hint=_(
                    "This option enables you to set a bandwidth limit for the guest network, "
                    "so that your main network doesn't get slowed-down by it."
                ),
            ).requires("guest_network_enabled", True)

            guest_network_section.add_field(
                Number,
                name="guest_network_qos_download", label=_("Download (kb/s)"),
                validators=[validators.PositiveInteger()],
                hint=_(
                    "Download speed in guest network (in kilobits per second)."
                ),
                default=1024,
            ).requires("guest_network_qos_enabled", True)
            guest_network_section.add_field(
                Number,
                name="guest_network_qos_upload", label=_("Upload (kb/s)"),
                validators=[validators.PositiveInteger()],
                hint=_(
                    "Upload speed in guest network (in kilobits per second)."
                ),
                default=1024,
            ).requires("guest_network_qos_enabled", True)

        def lan_form_cb(data):
            guest_network_enabled = data.get("guest_network_enabled", False)
            msg = {
                "ip": data["lan_ipaddr"],
                "netmask": data["lan_netmask"],
                "dhcp": {"enabled": data["dhcp_enabled"]},
                "guest_network": {"enabled": guest_network_enabled},
            }
            if data["dhcp_enabled"]:
                msg["dhcp"]["start"] = int(data["dhcp_min"])
                msg["dhcp"]["limit"] = int(data["dhcp_max"])

            if guest_network_enabled:
                msg["guest_network"]["ip"] = data["guest_network_ipaddr"]
                msg["guest_network"]["netmask"] = data["guest_network_netmask"]
                msg["guest_network"]["qos"] = {"enabled": data["guest_network_qos_enabled"]}
                if data["guest_network_qos_enabled"]:
                    msg["guest_network"]["qos"]["download"] = int(
                        data["guest_network_qos_download"])
                    msg["guest_network"]["qos"]["upload"] = int(
                        data["guest_network_qos_upload"])

            res = current_state.backend.perform("lan", "update_settings", msg)
            return "save_result", res  # store {"result": ...} to be used later...

        lan_form.add_callback(lan_form_cb)

        return lan_form
