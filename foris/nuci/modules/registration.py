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


class RegNum(YinElement):
    tag = "reg-num"
    NS_URI = "http://www.nic.cz/ns/router/registration"

    def __init__(self, value):
        super(RegNum, self).__init__()
        self.value = value

    @staticmethod
    def from_element(element):
        value = element.find(RegNum.qual_tag(RegNum.tag)).text
        return RegNum(value)

    @staticmethod
    def rpc_get():
        get_tag = RegNum.qual_tag("get")
        return ET.Element(get_tag)


class Serial(YinElement):
    tag = "serial"
    NS_URI = "http://www.nic.cz/ns/router/registration"

    def __init__(self, value):
        super(Serial, self).__init__()
        self.raw = value
        try:
            self.decimal = int(value, 16)
        except ValueError:
            self.decimal = None

    @staticmethod
    def from_element(element):
        value = element.find(Serial.qual_tag(Serial.tag)).text
        return Serial(value)

    @staticmethod
    def rpc_serial():
        get_tag = Serial.qual_tag("serial")
        return ET.Element(get_tag)


class RegistrationStatus(YinElement):
    tag = "get-status"
    NS_URI = "http://www.nic.cz/ns/router/registration"

    OWNED = "owned"
    FOREIGN = "foreign"
    FREE = "free"
    UNKNOWN = "unknown"

    STATUS_VALUES = {
        'owned': OWNED,
        'foreign': FOREIGN,
        'free': FREE,
    }

    def __init__(self, status, url=None, reg_num=None):
        super(RegistrationStatus, self).__init__()
        self.status = status
        self.url = url
        self.reg_num = reg_num

    @staticmethod
    def from_element(element):
        container = element.find(RegistrationStatus.qual_tag(RegistrationStatus.tag))
        status_raw = container.find(RegistrationStatus.qual_tag("status")).text
        status = RegistrationStatus.STATUS_VALUES.get(status_raw, RegistrationStatus.UNKNOWN)
        url_el = container.find(RegistrationStatus.qual_tag("url"))
        url = url_el.text if url_el is not None else None
        reg_num = container.find(RegistrationStatus.qual_tag("reg-num")).text

        return RegistrationStatus(status, url=url, reg_num=reg_num)

    @staticmethod
    def rpc_get_status(email, lang=None):
        get_status_tag = RegistrationStatus.qual_tag("get-status")
        element = ET.Element(get_status_tag)
        email_tag = RegistrationStatus.qual_tag("email")
        email_elem = ET.SubElement(element, email_tag)
        email_elem.text = email
        if lang:
            lang_tag = RegistrationStatus.qual_tag("lang")
            lang_elem = ET.SubElement(element, lang_tag)
            lang_elem.text = lang
        return element


class ContractUpdate(YinElement):
    tag = "contract-update"
    NS_URI = "http://www.nic.cz/ns/router/registration"

    @property
    def rcp_update_contract(self):
        """
        Generate rpc xml for update contracts
        """
        update_tag = ContractUpdate.qual_tag(ContractUpdate.tag)
        return ET.Element(update_tag)


####################################################################################################
ET.register_namespace("registration", RegNum.NS_URI)
