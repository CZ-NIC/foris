from .base import BaseConfigHandler

from foris import fapi
from foris import validators

from foris.core import gettext_dummy as gettext, ugettext as _
from foris.form import Checkbox, Textbox
from foris.nuci.filters import create_config_filter
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option
from foris.utils import contract_valid


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
        if resolver and resolver.value == "kresd":
            dns_main.add_field(
                Checkbox, name="dhcp_from_dns", label=_("Enable DNS from DHCP"),
                hint=_(
                    "This will enable your DNS resolver to insert DHCP client names among "
                    "the local DNS records."
                ),
                nuci_path="uci.resolver.kresd.dynamic_domains",
                nuci_preproc=lambda val: bool(int(val.value)), default=False,
            )
            dns_main.add_field(
                Textbox, name="dhcp_dns_domain", label=_("DNS domain of DHCP"),
                hint=_(
                    "This domain name will be used as a TLD (top level domain) of your "
                    "DNS records obtained using DHCP. E.g. if you have a client called "
                    "`android-1234` and domain set to `lan`, the client will be reachable "
                    "under domain name `android-1234.lan`."
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
                kresd = resolver.add(Section("kresd", "resolver"))
                kresd.add(Option("dynamic_domains", data['dhcp_from_dns']))

            if 'dhcp_dns_domain' in data:
                dhcp = uci.add(Config("dhcp"))
                dnsmasq_section = dns_form.nuci_config.find_child("uci.dhcp.@dnsmasq[0]")
                dnsmasq = dhcp.add(Section(dnsmasq_section.name, "dnsmasq", anonymous=True))
                dnsmasq.add(Option("local", "/%s/" % data["dhcp_dns_domain"].strip("/")))

            return "edit_config", uci

        dns_form.add_callback(dns_form_cb)
        return dns_form
