# coding=utf-8
# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2019 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

from foris import __version__ as version
from foris.langs import DEFAULT_LANGUAGE

logger = logging.getLogger("foris.state")


class ForisState(object):
    def __init__(self):
        self.foris_version = version
        self.language = DEFAULT_LANGUAGE
        self.app = None
        self.reboot_required = False
        self.assets_path = None
        self.sentry_running = False

    def update_lang(self, lang):
        logger.debug(f"current lang updated to '{lang}'")
        self.language = lang

    def set_app(self, app):
        logger.debug(f"current app updated to '{app}'")
        self.app = app

    def set_backend(self, backend):
        if backend.name in ["ubus", "unix-socket"]:
            logger.debug(f"setting backend to '{backend.name}' (path {backend.path}).")
        elif backend.name == "mqtt":
            logger.debug(
                f"setting backend to '{backend.name}' (host {backend.host}:{backend.port})."
            )
        self.backend = backend

    def set_websocket(self, ws_port, ws_path, wss_port, wss_path):
        self.websockets = {
            "ws_port": ws_port,
            "ws_path": ws_path,
            "wss_port": wss_port,
            "wss_path": wss_path,
        }

    def update_reboot_required(self, required):
        """ Sets reboot required indicator
        :param required: True if reboot is required False otherwise
        :type required: boolean
        """
        logger.debug(f"setting reboot_required={required}")
        self.reboot_required = required

    def update_notification_count(self, new_count):
        """ Updates notificaton count

        :param new_count: new notificaton count
        :type new_count: int
        """
        logger.debug(f"setting notification_count={new_count}")
        self.notification_count = new_count

    def repr(self):
        return "%s (%s)" % (self.__class__, str(vars(self)))

    def set_updater_is_running(self, running):
        """ Sets whether updater is running
        :param running: True if updater is running False otherwise
        :type running: boolean
        """
        logger.debug(f"setting updater_is_running={running}")
        self.updater_is_running = running

    def set_turris_os_version(self, version):
        """ Sets turris_os_version
        :param version: turrisOS version
        :type version: str
        """
        self.turris_os_version = version

    def set_device(self, device):
        """ Sets device
        :param device: device where this web gui is running (omnia/mox/...)
        :type device: str
        """
        self.device = device

    def update_password_set(self, password_set):
        logger.debug(f"setting password_set={password_set}")
        self.password_set = password_set

    def update_guide(self, guide_data):
        from foris.guide import Guide

        logger.debug(f"setting guide_data ({guide_data})")
        self.guide = Guide(guide_data)

    def set_assets_path(self, assets_path):
        logger.debug(f"setting assets_path to '{assets_path}'")
        self.assets_path = assets_path

    def set_sentry(self, running):
        logger.debug(f"setting sentry_running to '{running}'")
        self.sentry_running = running


current_state = ForisState()
