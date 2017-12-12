# coding=utf-8
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

from foris import DEVICE_CUSTOMIZATION, __version__ as version
from foris.langs import DEFAULT_LANGUAGE

logger = logging.getLogger("foris.state")


class ForisState(object):
    def __init__(self):
        self.device_customization = DEVICE_CUSTOMIZATION
        self.foris_version = version
        self.language = DEFAULT_LANGUAGE
        self.app = None
        self.reboot_required = False

    def update_lang(self, lang):
        logger.debug("current lang updated to '%s'" % lang)
        self.language = lang

    def set_app(self, app):
        logger.debug("current app updated to '%s'" % app)
        self.app = app

    def set_backend(self, backend):
        logger.debug("setting backend to '%s' (path %s)." % (backend.name, backend.path))
        self.backend = backend

    def update_reboot_required(self, required):
        """ Sets reboot required indicator
        :param required: True if reboot is required False otherwise
        :type required: boolean
        """
        logger.debug("setting reboot_required=%s" % required)
        self.reboot_required = required

    def repr(self):
        return "%s (%s)" % (self.__class__, str(vars(self)))


current_state = ForisState()
