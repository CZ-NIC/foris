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

import bottle
import logging

logger = logging.getLogger("utils.routing")


def reverse(name, **kargs):
    try:
        return bottle.app().router.build(name, **kargs)
    except bottle.RouteBuildError:
        for route in bottle.app().routes:
            if route.config.get("mountpoint"):
                config = route.config
                try:
                    return "%s%s" % (config['mountpoint.prefix'].rstrip("/"),
                                     config['mountpoint.target'].router.build(name, **kargs))
                except bottle.RouteBuildError as e:
                    if str(e).startswith("Missing URL"):
                        raise e
    raise bottle.RouteBuildError("No route with name '%s' in main app or mounted apps." % name)