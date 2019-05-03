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


def ip_str_to_num_4(ip_str):
    """ Converts IPv4 to number
    :param ip_str: str
    :return: int
    """
    res = 0
    try:
        for e in ip_str.split("."):
            res = res << 8
            res += int(e)
    except:
        raise ValueError("Incorrect IPv4 format %s" % repr(ip_str))
    return res


def ip_num_to_str_4(ip_number):
    """ Converts number to IPv4
    :param ip_number: int
    :return: str
    """
    res = []
    for i in range(4):
        res.append(str(ip_number & 0xFF))
        ip_number = ip_number >> 8
    return ".".join(reversed(res))


def normalize_subnet_4(ip_address, mask):
    """ 1.2.3.4 255.255.0.0 -> 1.2.0.0
    :param ip_address: str
    :param mask: str
    :return ip address: str
    """
    return ip_num_to_str_4(ip_str_to_num_4(ip_address) & ip_str_to_num_4(mask))


def mask_to_prefix_4(mask):
    """ 255.255.255.0 -> 24
    :param mask: str
    :return prefix: int
    """
    return "{0:b}".format(ip_str_to_num_4(mask)).count("1")


def prefix_to_mask_4(subnet):
    """ 255.255.255.0 -> 24
    :param prefix: int
    :return mask: str
    """
    return ip_num_to_str_4(int("1" * subnet + "0" * (32 - subnet), 2))
