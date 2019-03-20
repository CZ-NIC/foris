#
# Foris
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


from .base import ConfigPageMixin, JoinedPages

from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext


class AboutConfigPage(ConfigPageMixin):
    slug = "about"
    menu_order = 99

    template = "config/about"
    template_type = "jinja2"
    userfriendly_title = gettext("About")

    def render(self, **kwargs):
        data = current_state.backend.perform("about", "get")
        # process dates etc
        return self.default_template(data=data, **kwargs)
