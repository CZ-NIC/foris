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

"""
This module contains filters used for subtree filtering in nuci client. Filter is basically
an XML element that is passed to client.get() function and appropriate subtree is returned.
"""
from __future__ import absolute_import

import xml.etree.cElementTree as ET

from .modules import stats, time, uci_raw, updater, user_notify


# top-level containers
uci = ET.Element(uci_raw.Uci.qual_tag(uci_raw.Uci.tag))
updater = ET.Element(updater.Updater.qual_tag(updater.Updater.tag))
time = ET.Element(time.Time.qual_tag(time.Time.tag))
stats = ET.Element(stats.Stats.qual_tag(stats.Stats.tag))
messages = ET.Element(user_notify.Messages.qual_tag(user_notify.Messages.tag))


def create_config_filter(*args):
    """Factory method for Uci configs - creates filters for one
    or more configs"""
    _uci = uci_raw.Uci()
    for name in args:
        _uci.add(uci_raw.Config(name))
    return _uci.get_xml()


def create_uci_filter(config, section=None, option=None):
    uci_et = ET.Element(uci_raw.Uci.qual_tag(uci_raw.Uci.tag))
    config_et = ET.SubElement(uci_et, uci_raw.Uci.qual_tag("config"))
    ET.SubElement(config_et, uci_raw.Uci.qual_tag("name")).text = config
    if section:
        section_et = ET.SubElement(config_et, uci_raw.Uci.qual_tag("section"))
        ET.SubElement(section_et, uci_raw.Uci.qual_tag("name")).text = section
        if option:
            option_et = ET.SubElement(section_et, uci_raw.Uci.qual_tag("option"))
            ET.SubElement(option_et, uci_raw.Uci.qual_tag("name")).text = option

    return uci_et


def wifi_filter():

    uci = uci_raw.Uci()

    wireless_conf = uci_raw.Config("wireless")
    uci.add(wireless_conf)

    network_conf = uci_raw.Config("network")
    uci.add(network_conf)
    network_conf.add(uci_raw.Section("guest_turris", "interface"))

    firewall_conf = uci_raw.Config("firewall")
    uci.add(firewall_conf)  # get the whole firewall config - unable to filter

    dhcp_conf = uci_raw.Config("dhcp")
    uci.add(dhcp_conf)
    dhcp_conf.add(uci_raw.Section("guest_turris", "dhcp"))

    return uci.get_xml()


foris_config = create_config_filter("foris")
