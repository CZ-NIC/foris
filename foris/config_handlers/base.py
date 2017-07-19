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
import logging

from foris.utils.addresses import (
    ip_num_to_str_4, ip_str_to_num_4, prefix_to_mask_4, mask_to_prefix_4
)

from foris.nuci.modules.uci_raw import Config, Section, Option, List, Value

logger = logging.getLogger(__name__)


DEFAULT_GUEST_NETWORK = "10.111.222.0"
DEFAULT_GUEST_MASK = "255.255.255.0"
DEFAULT_GUEST_PREFIX = mask_to_prefix_4(DEFAULT_GUEST_MASK)


class BaseConfigHandler(object):
    def __init__(self, data=None):
        self.data = data
        self.__form_cache = None

    @property
    def form(self):
        if self.__form_cache is None:
            self.__form_cache = self.get_form()
        return self.__form_cache

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


def prepare_guest_configs(uci, enabled, network, prefix, interfaces=[], qos={}):
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
    interface_section.add(Option("type", "bridge"))
    if interfaces:
        interface_section.add(Option("ifname", " ".join(interfaces)))
    interface_section.add(Option("proto", "static"))
    interface_section.add(Option("ipaddr", router_ip))
    interface_section.add(Option("netmask", netmask))
    interface_section.add(Option("bridge_empty", "1"))

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
    dhcp_conf.add_replace(dhcp_section)
    dhcp_section.add(Option("interface", "guest_turris"))
    dhcp_section.add(Option("start", "200"))
    dhcp_section.add(Option("limit", "50"))
    dhcp_section.add(Option("leasetime", "1h"))
    dhcp_section.add(Option("ignore", ignore))
    dhcp_option_list = List("dhcp_option")
    dhcp_option_list.add(Value(0, "6,%s" % router_ip))
    dhcp_section.add(dhcp_option_list)

    # update qos part
    if qos:
        qos_conf = uci.find_child("sqm") or Config("sqm")
        uci.add(qos_conf)

        queue_section = qos_conf.add_replace(Section("guest_limit_turris", "queue"))
        queue_section.add(Option("enabled", qos["enabled"]))
        if qos["enabled"]:
            queue_section.add(Option("interface", "br-guest_turris"))
            queue_section.add(Option("qdisc", "fq_codel"))
            queue_section.add(Option("script", "simple.qos"))
            queue_section.add(Option("link_layer", "none"))
            queue_section.add(Option("verbosity", "5"))
            queue_section.add(Option("debug_logging", "1"))
            # We need to swap dowload and upload
            # "upload" means upload to the guest network
            # "download" means dowload from the guest network
            # so it would be confusing for a client who tries to run some speedtest
            queue_section.add(Option("download", qos["upload"]))
            queue_section.add(Option("upload", qos["download"]))
