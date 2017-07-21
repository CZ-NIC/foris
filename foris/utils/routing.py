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
import re
import logging

logger = logging.getLogger("utils.routing")


def _get_prefix_and_script_name():
    script_name = bottle.request.script_name
    prefix = bottle.request.app.config.get("prefix")
    if prefix:
        path_depth = len([p for p in prefix.split('/') if p])
        script_name, path_info = bottle.path_shift(script_name, "/", -path_depth)
    return script_name, prefix


def _normalize_path_end(path):
    """ a/b/c// -> a/b/c/ """
    return re.sub(r"/+$", "/", path)


def external_route(path):
    """ return external to another foris application (wizard/config) """
    script_name, _ = _get_prefix_and_script_name()
    script_name = script_name.strip("/")
    path = path.lstrip("/")
    if not script_name:
        return "/" + path

    return "/" + "/".join(script_name.split("/")[:-1] + [path])


def reverse(name, **kargs):
    script_name, prefix = _get_prefix_and_script_name()
    try:
        path = bottle.app().router.build(name, **kargs)
        return _normalize_path_end("".join([script_name.rstrip("/"), path]))
    except bottle.RouteBuildError:
        for route in bottle.app().routes:
            if route.config.get("mountpoint"):
                config = route.config
                try:
                    prefix = config['mountpoint.prefix'].rstrip("/")
                    path = config['mountpoint.target'].router.build(name, **kargs)
                    return _normalize_path_end(
                        "".join([script_name.rstrip("/"), prefix, path]))
                except bottle.RouteBuildError as e:
                    if str(e).startswith("Missing URL"):
                        raise e
    raise bottle.RouteBuildError("No route with name '%s' in main app or mounted apps." % name)


def static(name, *args):
    script_name, _ = _get_prefix_and_script_name()
    script_name = script_name.strip('/')
    script_name = "/%s" % script_name if script_name else ""
    return ("%s/static/%s" % (script_name, name)) % args
