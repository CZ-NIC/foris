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
import hashlib
import logging
import os
import re

from foris import BASE_DIR
from foris.state import current_state
from foris.utils.dynamic_assets import store_template
logger = logging.getLogger("utils.routing")

static_md5_map = {
}


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
    """ return external to another foris application (config/...) """
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


def generated_static(name, *args):
    lang = bottle.request.app.lang
    store_template(name, lang)
    name = "generated/%s/%s" % (lang, name.lstrip("/"))
    return static(name, *args)


def static(name, *args):
    script_name, _ = _get_prefix_and_script_name()
    script_name = script_name.strip('/')
    script_name = "/%s" % script_name if script_name else ""
    filename = ("%s/static/%s" % (script_name, name)) % args
    md5 = static_md5("static/" + name)
    return "%s?md5=%s" % (filename, md5) if md5 else filename


def static_md5(filename):
    """ return static file
    :param filename: url path
    :type filename: str
    :return: md5 of the file or none if the file is not found
    """
    filename = filename.lstrip("/")
    if filename in static_md5_map:
        return static_md5_map[filename]

    match = re.match(r'(?:static)?/*plugins/+(\w+)/+(.+)', filename)
    os_path = None
    if match:
        plugin_name, plugin_file = match.groups()
        # find correspoding plugin
        for plugin in bottle.app().foris_plugin_loader.plugins:
            if plugin.PLUGIN_NAME == plugin_name:
                os_path = os.path.join(plugin.DIRNAME, "static", plugin_file)
    else:
        match = re.match(r'(?:static)?/*generated/+([a-z]{2})/+(.+)', filename)
        if match:
            language, template = match.groups()
            os_path = os.path.join(current_state.assets_path, current_state.app, language, template)
        else:
            os_path = os.path.join(BASE_DIR, filename)

    if not os_path:
        logger.warning("Unable to find file for static url '%s'" % filename)
        return None

    if not os.path.exists(os_path):
        logger.warning("Static file '%s' related to url '%s' does not exist" % (os_path, filename))
        return None

    md5 = hashlib.md5()
    with open(os_path) as f:
        content = f.read()
        md5.update(content)

    digest = md5.hexdigest()
    static_md5_map[filename] = digest
    return digest


def get_root():
    root = bottle.request.script_name
    root = root.strip('/')
    root = "/%s" % root if root else ""
    return root
