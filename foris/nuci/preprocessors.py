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


from foris.nuci.modules.uci_raw import parse_uci_bool
from foris.utils import addresses


def guest_network_enabled(data):
    """ Processes the data obtained by `filters.wifi_filter`
    and decides whether guest network is enabled

    :param data: Data obtained from the query
    :type data: nuci.modules.base.Data
    :return: True if guest network is available False otherwise
    :rtype: bool
    """

    def test_enabled(uci_path, default=False):
        node = data.find_child(uci_path)
        if not node:
            return default
        return parse_uci_bool(node.value)

    if not test_enabled('uci.network.guest_turris.enabled') \
            or test_enabled('uci.dhcp.guest_turris.ignore', True) \
            or not test_enabled('uci.firewall.guest_turris.enabled') \
            or not test_enabled('uci.firewall.guest_turris_forward_wan.enabled') \
            or not test_enabled('uci.firewall.guest_turris_dhcp_rule.enabled') \
            or not test_enabled('uci.firewall.guest_turris_dns_rule.enabled'):
        return False

    return True


def generate_network_preprocessor(address_path, netmask_path, default_network, default_netmask):
    """ Generates a preprocessor for converting network na netmask to an ip with subnet
    192.168.1.1 -> 192.168.1.1/24

    :param address_path: uci path for the network
    :type address_path: str
    :param netmask_path: uci path for the netmask
    :type netmask_path: str
    :param default_network: default network which will be used if no network is present
    :type default_network: str
    :param default_netmask: default netmask which will be used if no network is present
    :type default_netmask: str

    :return: preprocessor function
    :rtype: callable
    """

    def network_preprocessor(data):
        """
        :param data: Data obtained from the query
        :type data: nuci.modules.base.Data
        """
        address_node = data.find_child(address_path)
        address = address_node.value if address_node else default_network
        netmask_node = data.find_child(netmask_path)
        netmask = netmask_node.value if netmask_node else default_netmask

        try:
            prefix = addresses.mask_to_prefix_4(netmask)
        except ValueError:
            netmask = default_netmask
            prefix = addresses.mask_to_prefix_4(default_netmask)

        try:
            address = addresses.normalize_subnet_4(address, netmask)
        except ValueError:
            address = addresses.normalize_subnet_4(default_network, netmask)

        return "%s/%d" % (address, prefix)

    return network_preprocessor

