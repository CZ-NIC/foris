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

from nuci.modules import stats, time, uci_raw, updater
import xml.etree.cElementTree as ET


# top-level containers
uci = ET.Element(uci_raw.Uci.qual_tag("uci"))
updater = ET.Element(updater.Updater.qual_tag("updater"))
time = ET.Element(time.Time.qual_tag("time"))
stats = ET.Element(stats.Stats.qual_tag("stats"))


# factory for uci configs
def create_uci_config(config_name):
    _uci = uci_raw.Uci()
    _config = uci_raw.Config(config_name)
    _uci.add(_config)
    return _config.get_tree()


foris_config = create_uci_config("foris")
