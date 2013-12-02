# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <www.nic.cz>
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
import client

__all__ = ['add_config_update', 'commit']

logger = logging.getLogger("nuci.configurator")

config_updates = []
field_updates = {}


def add_config_update(yin_element):
    """Serves for altering more complicated structures in Nuci configuration
    (i.e. not key = value).

    :param yin_element:
    :return:
    """
    config_updates.append(yin_element)


def clean_updates():
    global config_updates, field_updates
    config_updates = []
    field_updates = {}


def commit():
    logger.debug("Commiting changes.")
    client.edit_config_multiple([cu.get_xml() for cu in config_updates])
    clean_updates()