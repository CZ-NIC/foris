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

from __future__ import absolute_import

import ubus
import logging
import json

logger = logging.getLogger("ubus")


if not ubus.get_connected():
    logger.debug("Connecting to ubus.")
    ubus.connect()


def call(obj, func, params):
    logger.debug("Calling function '%s'.'%s' with params '%s'" % (obj, func, json.dumps(params)))
    return ubus.call(obj, func, params)
