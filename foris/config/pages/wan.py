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

import bottle

from foris.config_handlers import wan
from foris.state import current_state

from .base import ConfigPageMixin, JoinedPages


class WanConfigPage(ConfigPageMixin, wan.WanHandler):
    slug = "wan"
    menu_order = 15

    template = "config/wan"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs['interface_count'] = self.backend_data["interface_count"]
        kwargs['interface_up_count'] = self.backend_data["interface_up_count"]
        kwargs['wan_status'] = self.status_data
        return super(WanConfigPage, self).render(**kwargs)

    def _action_check_connection(self, ipv6=True):
        return current_state.backend.perform(
            "wan", "connection_test_trigger", {"test_kinds": ["ipv4", "ipv6"] if ipv6 else ["ipv4"]}
        )

    def call_ajax_action(self, action):
        if action == "check-connection":
            ipv6_type = bottle.request.GET.get("ipv6_type")
            return self._action_check_connection(ipv6_type != "none")
        raise ValueError("Unknown AJAX action.")
