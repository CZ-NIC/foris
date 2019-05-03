# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2017 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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


logger = logging.getLogger("foris.caches")


class SimpleCache(dict):
    def __init__(self, name):
        self.name = name

    def clear(self):
        super(SimpleCache, self).clear()
        logger.debug("Cache %s cleared.", self.name)

    def __setitem__(self, key, value):
        super(SimpleCache, self).__setitem__(key, value)
        logger.debug("Cache %s: '%s' -> '%s'.", self.name, key, value)


class PerRequest(object):
    """
    Ceched per request
    """

    backend_data = SimpleCache("backend_data")


per_request = PerRequest
