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

from base import YinElement
from xml.etree import cElementTree as ET


class Updater(YinElement):
    tag = "updater"
    NS_URI = "http://www.nic.cz/ns/router/updater"

    def __init__(self, running, failed, last_activity):
        super(Updater, self).__init__()
        self.running = running
        self.failed = failed
        self.last_activity = last_activity

    @staticmethod
    def from_element(element):
        running = element.find(Updater.qual_tag("running"))
        running = running.text if running is not None else False
        failed = element.find(Updater.qual_tag("failed"))
        failed = failed.text if failed is not None else False
        activities_elem = element.find(Updater.qual_tag("last_activity"))
        last_activity = []
        if activities_elem is not None:
            for activity_elem in activities_elem.iter():
                if activity_elem.tag == Updater.qual_tag("install"):
                    last_activity.append(('install', activity_elem.text))
                elif activity_elem.tag == Updater.qual_tag("remove"):
                    last_activity.append(('remove', activity_elem.text))
        return Updater(running, failed, last_activity)

    @property
    def key(self):
        return "updater"

####################################################################################################
ET.register_namespace("updater", Updater.NS_URI)
