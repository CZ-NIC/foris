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

from foris.utils.translators import get_current_language


class LanguageSwitchMiddleware(object):
    """ Updates language settings based on actual settings which is stored in a config file.

    There can be a few running instances of foris apps (e.g wizard config).
    When one changes the language the other should reflect the change immediatelly.
    Therefor it is necessary to update the langage every request with a language query.
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        get_current_language()  # it also sets the current languge in the app state structure
        return self.app(environ, start_response)
