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

from .base import BaseConfigHandler

from foris import fapi
from foris import validators

from foris.form import Checkbox, Textbox
from foris.state import current_state
from foris.utils import contract_valid
from foris.utils.translators import gettext_dummy as gettext, _


class DNSHandler(BaseConfigHandler):
    """
    DNS-related settings
    """

    userfriendly_title = gettext("DNS")

    def get_form(self):
        data = current_state.backend.perform("dns", "get_settings")
        data["dnssec_disabled"] = not data["dnssec_enabled"]
        if self.data:
            # Update from post
            data.update(self.data)
            data["dnssec_enabled"] = not self.data.get("dnssec_disabled", False)

        dns_form = fapi.ForisForm("dns", data)
        dns_main = dns_form.add_section(name="set_dns", title=_(self.userfriendly_title))
        dns_main.add_field(
            Checkbox, name="forwarding_enabled", label=_("Use forwarding"),
            preproc=lambda val: bool(int(val)),
        )

        if not contract_valid():
            dns_main.add_field(
                Checkbox, name="dnssec_disabled", label=_("Disable DNSSEC"),
                preproc=lambda val: bool(int(val)), default=False
            )

        dns_main.add_field(
            Checkbox, name="dns_from_dhcp_enabled", label=_("Enable DHCP clients in DNS"),
            hint=_(
                "This will enable your DNS resolver to place DHCP client's "
                "names among the local DNS records."
            ),
            preproc=lambda val: bool(int(val)), default=False,
        )
        dns_main.add_field(
            Textbox, name="dns_from_dhcp_domain", label=_("Domain of DHCP clients in DNS"),
            hint=_(
                "This domain will be used as prefix. E.g. The result for client \"android-123\" "
                "and domain \"my.lan\" will be \"android-123.my.lan\"."
            ),
            validators=[validators.Domain()],
        ).requires("dns_from_dhcp_enabled", True)

        def dns_form_cb(data):
            msg = {
                "dnssec_enabled": not data.get("dnssec_disabled", False),
                "forwarding_enabled": data["forwarding_enabled"],
                "dns_from_dhcp_enabled": data["dns_from_dhcp_enabled"],
            }
            if "dns_from_dhcp_domain" in data:
                msg["dns_from_dhcp_domain"] = data["dns_from_dhcp_domain"]
            res = current_state.backend.perform("dns", "update_settings", msg)
            return "save_result", res  # store {"result": ...} to be used later...

        dns_form.add_callback(dns_form_cb)
        return dns_form
