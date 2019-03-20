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
#


from foris.config_handlers import dns
from foris.state import current_state


from .base import ConfigPageMixin


class DNSConfigPage(ConfigPageMixin, dns.DNSHandler):
    slug = "dns"
    menu_order = 19

    template = "config/dns"
    template_type = "jinja2"

    def _action_check_connection(self):
        return current_state.backend.perform(
            "wan", "connection_test_trigger", {"test_kinds": ["dns"]})

    def call_ajax_action(self, action):
        if action == "check-connection":
            return self._action_check_connection()
        raise ValueError("Unknown AJAX action.")
