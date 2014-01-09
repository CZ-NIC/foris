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


class Maintain(YinElement):
    tag = "maintain"
    NS_URI = "http://www.nic.cz/ns/router/maintain"

    def __init__(self, data):
        """

        :param data: base64 encoded .tar.xz backup file
        :return:
        """
        super(Maintain, self).__init__()
        self.data = data

    @staticmethod
    def from_element(element):
        data = element.find(Maintain.qual_tag("data")).text
        return Maintain(data)

    @property
    def key(self):
        return "maintain"

    @staticmethod
    def rpc_reboot():
        """
        Request a system reboot.
        """
        backup_tag = Maintain.qual_tag("reboot")
        element = ET.Element(backup_tag)
        return element

    @staticmethod
    def rpc_config_backup():
        """
        Request for a configuration backup from Nuci.
        """
        backup_tag = Maintain.qual_tag("config-backup")
        element = ET.Element(backup_tag)
        return element

    @staticmethod
    def rpc_config_restore(filename):
        """
        Request for a configuration restore from a file with a given
        filename.

        :return:
        """
        restore_tag = Maintain.qual_tag("config-restore")
        element = ET.Element(restore_tag)
        data_tag = Maintain.qual_tag("data")
        data_elem = ET.SubElement(element, data_tag)
        data_elem.text = filename  # TODO: read and encode the file
        return element

####################################################################################################
ET.register_namespace("maintain", Maintain.NS_URI)