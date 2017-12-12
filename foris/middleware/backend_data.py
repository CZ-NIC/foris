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

import bottle

from foris.state import current_state


class BackendData(object):
    """ Reads data from the backend and stores it properly.
        This is performed everytime when a request arrives.

        There can be a few running instances of foris apps (e.g wizard config).
        When one changes the other should reflect the change immediatelly.
        Therefor it is necessary to update it so frequent.
    """

    def set_language(self, language):
        """ Sets the language internallly inside the running instance of foris

        :param language: language to be set
        :type language: str
        """

        # Update info variable
        current_state.update_lang(language)

        # update bottle app as well
        bottle.app().lang = language

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        data = current_state.backend.perform("web", "get_data", {})

        # update language
        self.set_language(data["language"])

        # update reboot required
        current_state.update_reboot_required(data["reboot_required"])

        return self.app(environ, start_response)
