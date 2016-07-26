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

from xml.etree import ElementTree as ET

from base import YinElement
from ..utils import LocalizableTextValue


class Updater(YinElement):
    tag = "updater"
    NS_URI = "http://www.nic.cz/ns/router/updater"

    def __init__(self, running, failed, last_activity, offline_pending, pkg_list):
        super(Updater, self).__init__()
        self.running = running
        self.failed = failed
        self.last_activity = last_activity
        self.offline_pending = offline_pending
        self.pkg_list = pkg_list

    @staticmethod
    def from_element(element):
        running = element.find(Updater.qual_tag("running"))
        running = running.text if running is not None else False
        failed = element.find(Updater.qual_tag("failed"))
        failed = failed.text if failed is not None else False
        offline_pending = element.find(Updater.qual_tag("offline-pending"))
        offline_pending = True if offline_pending is not None else False
        activities_elem = element.find(Updater.qual_tag("last_activity"))
        last_activity = []
        if activities_elem is not None:
            for activity_elem in activities_elem.iter():
                if activity_elem.tag == Updater.qual_tag("install"):
                    last_activity.append(('install', activity_elem.text))
                elif activity_elem.tag == Updater.qual_tag("remove"):
                    last_activity.append(('remove', activity_elem.text))
                elif activity_elem.tag == Updater.qual_tag("download"):
                    last_activity.append(('download', activity_elem.text))
        pkg_list_elements = element.findall(Updater.qual_tag("pkg-list"))
        pkg_list = []
        for item_el in pkg_list_elements:
            pkg_list.append(PackageListItem.from_element(item_el))

        return Updater(running, failed, last_activity, offline_pending, pkg_list)

    @property
    def key(self):
        return "updater"


class PackageListItem(object):
    def __init__(self, name, title, description):
        self.name = name
        self.title = title
        self.description = description

    @staticmethod
    def from_element(element):
        xml_lang_attr = "{http://www.w3.org/XML/1998/namespace}lang"

        name = element.find(Updater.qual_tag("name")).text
        title_els = element.findall(Updater.qual_tag("title"))
        title = LocalizableTextValue()
        for title_el in title_els:
            lang = title_el.get(xml_lang_attr)
            title.set_translation(lang, title_el.text)

        description_els = element.findall(Updater.qual_tag("description"))
        description = LocalizableTextValue()
        for description_el in description_els:
            lang = description_el.get(xml_lang_attr)
            description.set_translation(lang, description_el.text)

        return PackageListItem(name, title, description)

####################################################################################################
ET.register_namespace("updater", Updater.NS_URI)
