#
# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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
#

import logging
import shutil
import os
import hashlib
import bottle


logger = logging.getLogger("foris.utils.dynamic_assets")


dynamic_assets_map = {
}

current_assets_path = None


def reset(app_name, assets_path):
    """ Deletes generated assets and cleans md5
    """
    global dynamic_assets_map
    dynamic_assets_map = {}
    target = os.path.join(assets_path, app_name)
    logger.debug("cleaning dynamic assets in '%s'", target)
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target)
    global current_assets_path
    current_assets_path = target


def store_template(template_name, lang):
    """ Creates static file from template as stores it
    :param template_name: should looks like this <path>/<file>.tpl
    :type template_name: str
    """
    template_name = template_name.lstrip("/")
    logger.debug("Trying to store generated template '%s' (%s)", template_name, lang)

    # already present
    if (template_name, lang) in dynamic_assets_map:
        logger.debug("Template already generated '%s' (%s)", template_name, lang)
        return

    # store file
    rendered = bottle.template(template_name + ".tpl")
    target_path = os.path.join(current_assets_path, lang, template_name)
    try:
        os.makedirs(os.path.dirname(target_path))
    except os.error:
        # already exists
        pass
    with open(target_path, "w") as f:
        f.write(bytearray(rendered, "utf8"))
        f.flush()

    logger.debug(
        "Generated template '%s' (%s) was stored to '%s'.", template_name, lang, target_path)

    # mark present
    dynamic_assets_map[(template_name, lang)] = True


def regenerate(app_name, target_path, static_files_path, plugin_name=None):
    """
    :param plugin_name: None means no plugin just main app
    """
    target = os.path.join(target_path, app_name)
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target)

    # handle static files
    for root, _, files in os.walk(static_files_path):
        target_dir = root.replace(static_files_path, "", 1)
        target_dir = target_dir.lstrip("/")
        target_dir = os.path.join("static", target_dir)

        try:
            # TODO not that make dir has attribute exist_ok in pyton3 so it can be refactored
            # after migrating to python3
            os.makedirs(os.path.join(target, target_dir))
        except os.error:
            pass  # already created

        for filename in files:
            # copy file and store md5
            asset_name = os.path.join(target_dir, filename)
            src_path = os.path.join(root, filename)
            dest_path = os.path.join(target, target_dir, filename)
            md5 = hashlib.md5()

            with open(src_path) as src, open(dest_path, "w") as dest:
                content = src.read()
                md5.update(content)
                dest.write(content)

            digest = md5.hexdigest()
            logger.debug("static asset loaded %s '%s'" % (digest, asset_name))
            asset_map[asset_name] = {"md5": digest}
