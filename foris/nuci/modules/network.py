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

from foris.nuci.utils import unqualify


class Connection(YinElement):
    tag = "connection"
    NS_URI = "http://www.nic.cz/ns/router/network"

    def __init__(self, check_results):
        super(Connection, self).__init__()
        self.check_results = check_results

    @staticmethod
    def from_element(element):
        connection_el = element.find(Connection.qual_tag(Connection.tag))
        check_results = {}
        for elem in connection_el:
            check_results[unqualify(elem.tag)] = True if elem.text == "true" else False

        # It is confusing that DNSSEC test reports OK even if DNS does not work.
        # It's better to report DNSSEC as broken then, because we can't effectively
        # check its status.
        if "DNS" in check_results and "DNSSEC" in check_results:
            if not check_results['DNS']:
                check_results['DNSSEC'] = False

        return Connection(check_results)

    @staticmethod
    def rpc_check():
        get_tag = Connection.qual_tag("check")
        return ET.Element(get_tag)

####################################################################################################
ET.register_namespace("network", Connection.NS_URI)
