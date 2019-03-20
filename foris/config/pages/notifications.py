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

from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, _

from .base import ConfigPageMixin


class NotificationsConfigPage(ConfigPageMixin):
    slug = "notifications"

    menu_order = 9

    template = "config/notifications"
    userfriendly_title = gettext("Notifications")
    template_type = "jinja2"

    def render(self, **kwargs):
        notifications = current_state.backend.perform(
            "router_notifications", "list", {"lang": current_state.language}
        )["notifications"]

        # show only non displayed notifications
        kwargs["notifications"] = [e for e in notifications if not e["displayed"]]

        return super(NotificationsConfigPage, self).render(**kwargs)

    def _action_dismiss_notifications(self):
        notification_ids = bottle.request.POST.getall("notification_ids[]")
        response = current_state.backend.perform(
            "router_notifications", "mark_as_displayed", {"ids": notification_ids})
        return response["result"], notification_ids

    def call_ajax_action(self, action):
        if action == "dismiss-notifications":
            bottle.response.set_header("Content-Type", "application/json")
            res = self._action_dismiss_notifications()
            if res[0]:
                return {"success": True, "displayedIDs": res[1]}
            else:
                return {"success": False}

        elif action == "list":
            notifications = current_state.backend.perform(
                "router_notifications", "list", {"lang": current_state.language}
            )["notifications"]
            return bottle.template(
                "_notifications.html.j2",
                notifications=[e for e in notifications if not e["displayed"]],
                template_adapter=bottle.Jinja2Template,
            )

        raise ValueError("Unknown AJAX action.")

    @classmethod
    def get_menu_tag(cls):
        return {
            "show": True if current_state.notification_count else False,
            "hint": _("Number of notifications"),
            "text": "%d" % current_state.notification_count,
        }
