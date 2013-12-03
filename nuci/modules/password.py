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


class Password(YinElement):
    NS_URI = "http://www.nic.cz/ns/router/password"

    def __init__(self, user, password):
        super(Password, self).__init__()
        self.user = user
        self.password = password

    @property
    def rpc_set(self):
        set_tag = Password.qual_tag("set")
        element = ET.Element(set_tag)
        user_elem = ET.SubElement(element, Password.qual_tag("user"))
        user_elem.text = self.user
        password_elem = ET.SubElement(element, Password.qual_tag("password"))
        password_elem.text = self.password
        return element

####################################################################################################
ET.register_namespace("password", Password.NS_URI)