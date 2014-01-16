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
import logging

from base import YinElement
from xml.etree import cElementTree as ET
from nuci.utils import unqualify


class Stats(YinElement):
    """Stats element, contains information about runtime data.

    Data stored in dictionary Stats.data with following structure:

     Stats.data:
         -- 'uptime': system uptime (string)
         -- 'kernel-version': kernel version (string)
         -- 'meminfo': dict of memory information
         ---- 'MemTotal': total RAM
         ---- 'MemFree': free RAM
         ---- etc... (depending on content of meminfo element)
         -- 'serial-number-raw': serial number as returned by Nuci
         -- 'serial-number-decimal': serial number converted from base 16
                                     to base 10 (or None, if failed)
    """

    tag = "stats"
    NS_URI = "http://www.nic.cz/ns/router/stats"

    def __init__(self):
        super(Stats, self).__init__()
        self.data = {}

    @staticmethod
    def from_element(element):
        stats = Stats()
        for elem in element.findall("./*"):
            if elem.tag == Stats.qual_tag("uptime"):
                stats.data['uptime'] = elem.text
            elif elem.tag == Stats.qual_tag("kernel-version"):
                stats.data['kernel-version'] = elem.text
            elif elem.tag == Stats.qual_tag("serial-number"):
                stats.data['serial-number-raw'] = elem.text
                try:
                    stats.data['serial-number-decimal'] = int(elem.text, 16)
                except ValueError:
                    stats.data['serial-number-decimal'] = None
            elif elem.tag == Stats.qual_tag("meminfo"):
                stats.data['meminfo'] = {}
                for meminfo_elem in elem:
                    stats.data['meminfo'][unqualify(meminfo_elem.tag)] = meminfo_elem.text
        logging.info(unicode(stats.data))
        return stats

    @property
    def key(self):
        return "stats"

    def __str__(self):
        return "Device stats"

####################################################################################################
ET.register_namespace("stats", Stats.NS_URI)
