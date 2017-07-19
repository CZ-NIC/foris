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
from datetime import datetime, timedelta
from xml.etree import cElementTree as ET

from ..utils import unqualify

from .base import YinElement


class Stats(YinElement):
    """Stats element, contains information about runtime data.

    Data stored in dictionary Stats.data with following structure:

     Stats.data:
         -- 'uptime': system uptime (string)
         -- 'kernel-version': kernel version (string)
         -- 'turris-os-version': Turris OS version (string)
         -- 'model': router model - e.g. Turris, Turris Omnia, ... (string)
         -- 'board-name': board name - e.g. RTRS01, RTRS02, RTROM01, ... (string)
                          (please note that this name is capitalized by postprocessing method)
         -- 'hostname': router hostname (string)
         -- 'meminfo': dict of memory information
         ---- 'MemTotal': total RAM
         ---- 'MemFree': free RAM
         ---- etc... (depending on content of meminfo element)
         -- 'wireless-cards': list of wireless cards
         ---- [item]: wireless card properties
         ------ 'name': name of device
         ------ 'vte-capabilities': (boolean) whether the device has VTE capabilities
         ------ 'channels': list of available channels
         -------- 'number': (int) channel number
         -------- 'frequency': (int) frequency in MHz
         -------- 'disabled': (boolean) is channel disabled?
         -------- 'radar': (boolean) requires radar detection?
         -- 'interfaces': dict of interfaces
         ---- `key:value` interface stats (key = interface name)
         ------ 'is_up': link of interface - True if up, False if down, None else
         -- 'sending': dict of status of data sending
         ---- 'ucollect': (dict) status of uCollect
         ------ 'alive': (bool) whether sending works flawlessly
         ------ 'status': (string) status code/name
         ------ 'age': (int) last update of status in seconds
         ------ 'last_update': (datetime) time of last update
         ---- 'firewall': (dict) status of firewall
         ------ 'alive': (bool) whether sending works flawlessly
         ------ 'status': (string) status code/name
         ------ 'age': (int) last update of status in seconds
         ------ 'last_update': (datetime) time of last update
    """

    tag = "stats"
    NS_URI = "http://www.nic.cz/ns/router/stats"

    def __init__(self):
        super(Stats, self).__init__()
        self.data = {}

    @staticmethod
    def __postprocess_data(data):
        # capitalize board-name of Turris boards
        if data.get("model", "").lower().startswith("turris"):
            data['board-name'] = data.get("board-name", "").upper()
        return data

    @staticmethod
    def _update_sending(elem, component, sending_dict):
        component_dict = sending_dict.setdefault(component, {})
        for field_el in elem:
            if field_el.tag == Stats.qual_tag("status"):
                component_dict['status'] = field_el.text
                component_dict['alive'] = field_el.text == "online"
            elif field_el.tag == Stats.qual_tag("age"):
                try:
                    age = int(field_el.text)
                    component_dict['age'] = age
                    component_dict['last_update'] = datetime.now() - timedelta(seconds=age)
                except ValueError:
                    pass

    @staticmethod
    def from_element(element):
        stats = Stats()
        for elem in element.findall("./*"):
            if elem.tag == Stats.qual_tag("uptime"):
                stats.data['uptime'] = elem.text
            elif elem.tag == Stats.qual_tag("model"):
                stats.data['model'] = elem.text
            elif elem.tag == Stats.qual_tag("board-name"):
                stats.data['board-name'] = elem.text
            elif elem.tag == Stats.qual_tag("hostname"):
                stats.data['hostname'] = elem.text
            elif elem.tag == Stats.qual_tag("kernel-version"):
                stats.data['kernel-version'] = elem.text
            elif elem.tag == Stats.qual_tag("turris-os-version"):
                stats.data['turris-os-version'] = elem.text
            elif elem.tag == Stats.qual_tag("meminfo"):
                stats.data['meminfo'] = {}
                for meminfo_elem in elem:
                    stats.data['meminfo'][unqualify(meminfo_elem.tag)] = meminfo_elem.text
            elif elem.tag == Stats.qual_tag("wireless-cards"):
                stats.data['wireless-cards'] = []
                for wc_elem in elem:
                    wc = {
                        'name': wc_elem.find(Stats.qual_tag("name")).text,
                        'vht-capabilities': wc_elem.find(Stats.qual_tag("vht-capabilities")) is not None,
                        'channels': [],
                    }
                    for channel_el in wc_elem.iter(Stats.qual_tag("channel")):
                        channel = {
                            'number': int(channel_el.find(Stats.qual_tag("number")).text),
                            'frequency': int(channel_el.find(Stats.qual_tag("frequency")).text),
                            'disabled': channel_el.find(Stats.qual_tag("disabled")) is not None,
                            'radar': channel_el.find(Stats.qual_tag("radar")) is not None
                        }
                        wc['channels'].append(channel)
                    stats.data['wireless-cards'].append(wc)
            elif elem.tag == Stats.qual_tag("interfaces"):
                interfaces = stats.data['interfaces'] = {}
                for interface_elem in elem:
                    if_name = interface_elem.find(Stats.qual_tag("name")).text
                    is_up = interface_elem.find(Stats.qual_tag("up")) is not None
                    is_down = interface_elem.find(Stats.qual_tag("down")) is not None
                    interfaces[if_name] = {
                        'is_up': True if is_up else False if is_down else None
                    }
            elif elem.tag == Stats.qual_tag("ucollect-sending"):
                sending = stats.data.setdefault("sending", {})
                Stats._update_sending(elem, "ucollect", sending)
            elif elem.tag == Stats.qual_tag("firewall-sending"):
                sending = stats.data.setdefault("sending", {})
                Stats._update_sending(elem, "firewall", sending)

        # do postprocessing of data
        Stats.__postprocess_data(stats.data)

        return stats

    @property
    def key(self):
        return "stats"

    def __str__(self):
        return "Device stats"

####################################################################################################
ET.register_namespace("stats", Stats.NS_URI)
