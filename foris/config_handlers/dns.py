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
from foris.nuci.filters import create_config_filter
from foris.nuci.helpers import contract_valid
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option
from foris.utils.translators import gettext_dummy as gettext, _


class DNSHandler(BaseConfigHandler):
    """
    DNS-related settings, currently for enabling/disabling upstream forwarding
    """

    userfriendly_title = gettext("DNS")

    def get_form(self):
        dns_form = fapi.ForisForm("dns", self.data, filter=create_config_filter("resolver", "dhcp"))
        dns_main = dns_form.add_section(name="set_dns", title=_(self.userfriendly_title))
        dns_main.add_field(
            Checkbox, name="forward_upstream", label=_("Use forwarding"),
            nuci_path="uci.resolver.common.forward_upstream",
            nuci_preproc=lambda val: bool(int(val.value)), default=True
        )

        if not contract_valid():
            dns_main.add_field(
                Checkbox, name="ignore_root_key", label=_("Disable DNSSEC"),
                nuci_path="uci.resolver.common.ignore_root_key",
                nuci_preproc=lambda val: bool(int(val.value)), default=False,
            )

        resolver = dns_form.nuci_config.find_child("uci.resolver.common.prefered_resolver")
        if resolver and resolver.value in ["kresd", "unbound"]:
            dns_main.add_field(
                Checkbox, name="dhcp_from_dns", label=_("Enable DHCP clients in DNS"),
                hint=_(
                    "This will enable your DNS resolver to place DHCP client's "
                    "names among the local DNS records."
                ),
                nuci_path="uci.resolver.common.dynamic_domains",
                nuci_preproc=lambda val: bool(int(val.value)), default=False,
            )
            dns_main.add_field(
                Textbox, name="dhcp_dns_domain", label=_("Domain of DHCP clients in DNS"),
                hint=_(
                    "This domain will be used as TLD. E.g. The result for client \"android-123\" "
                    "and domain \"lan\" will be \"android-123.lan\"."
                ),
                nuci_path="uci.dhcp.@dnsmasq[0].local",
                nuci_preproc=lambda val: val.value.strip("/") if val else "lan", default="lan",
                validators=[validators.Domain()],
            ).requires("dhcp_from_dns", True)

        resolver = dns_form.nuci_config.find_child("uci.dhcp.@dnsmasq[0]")

        def dns_form_cb(data):
            uci = Uci()
            resolver = Config("resolver")
            uci.add(resolver)
            server = Section("common", "resolver")
            resolver.add(server)
            server.add(Option("forward_upstream", data['forward_upstream']))
            if not contract_valid():
                server.add(Option("ignore_root_key", data['ignore_root_key']))

            if 'dhcp_from_dns' in data:
                server.add(Option("dynamic_domains", data['dhcp_from_dns']))

            if 'dhcp_dns_domain' in data:
                dhcp = uci.add(Config("dhcp"))
                dnsmasq_section = dns_form.nuci_config.find_child("uci.dhcp.@dnsmasq[0]")
                dnsmasq = dhcp.add(Section(dnsmasq_section.name, "dnsmasq", anonymous=True))
                dnsmasq.add(Option("local", "/%s/" % data["dhcp_dns_domain"].strip("/")))

            return "edit_config", uci

        dns_form.add_callback(dns_form_cb)
        return dns_form
