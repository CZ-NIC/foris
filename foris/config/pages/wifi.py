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

from foris.config_handlers import wifi
from foris.state import current_state
from foris.utils import messages
from foris.utils.routing import reverse
from foris.utils.translators import _

from .base import ConfigPageMixin


class WifiConfigPage(ConfigPageMixin, wifi.WifiHandler):
    slug = "wifi"
    menu_order = 20

    template = "config/wifi"
    template_type = "jinja2"

    def _action_reset(self):

        if bottle.request.method != "POST":
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="wifi"))

        data = current_state.backend.perform("wifi", "reset")
        if "result" in data and data["result"] is True:
            messages.success(_("Wi-Fi reset was successful."))
        else:
            messages.error(_("Failed to perform Wi-Fi reset."))

        bottle.redirect(reverse("config_page", page_name="wifi"))

    def call_action(self, action):
        if action == "reset":
            self._action_reset()
        raise ValueError("Unknown action.")

    def save(self, *args, **kwargs):
        super(WifiConfigPage, self).save(no_messages=True, *args, **kwargs)
        return self.form.callback_results.get("result", None)
