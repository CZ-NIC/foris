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

import bottle
import base64

from datetime import datetime

from foris.config_handlers import backups, notifications
from foris.state import current_state
from foris.utils import messages
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, _

from .base import ConfigPageMixin


class MaintenanceConfigPage(ConfigPageMixin, backups.MaintenanceHandler):
    slug = "maintenance"
    menu_order = 21

    template = "config/maintenance"
    template_type = "jinja2"

    userfriendly_title = gettext("Maintenance")

    def _action_config_backup(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = "turris-backup-%s.tar.bz2" % timestamp
        data = current_state.backend.perform("maintain", "generate_backup")
        raw_data = base64.b64decode(data["backup"])

        bottle.response.set_header("Content-Type", "application/x-bz2")
        bottle.response.set_header("Content-Disposition", 'attachment; filename="%s"' % filename)
        bottle.response.set_header("Content-Length", len(raw_data))

        return raw_data

    def _action_save_notifications(self):
        if bottle.request.method != "POST":
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        handler = notifications.NotificationsHandler(bottle.request.POST.decode())
        if handler.save():
            messages.success(_("Configuration was successfully saved."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        messages.warning(_("There were some errors in your input."))
        return super(MaintenanceConfigPage, self).render(notifications_form=handler.form)

    def _action_test_notifications(self):
        if bottle.request.method != "POST":
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        data = current_state.backend.perform(
            "router_notifications",
            "create",
            {
                "msg": "_(This is a testing notification. Please ignore me.)",
                "severity": "news",
                "immediate": True,
            },
        )

        if data["result"]:
            messages.success(_("Testing message was sent, please check your inbox."))
        else:
            messages.error(
                _("Sending of the testing message failed, your configuration is possibly wrong.")
            )
        bottle.redirect(reverse("config_page", page_name="maintenance"))

    def call_action(self, action):
        if action == "config-backup":
            return self._action_config_backup()
        elif action == "save_notifications":
            return self._action_save_notifications()
        elif action == "test_notifications":
            return self._action_test_notifications()
        raise ValueError("Unknown AJAX action.")

    def render(self, **kwargs):
        notifications_handler = notifications.NotificationsHandler(self.data)
        return super(MaintenanceConfigPage, self).render(
            notifications_form=notifications_handler.form, **kwargs
        )

    def save(self, *args, **kwargs):
        super(MaintenanceConfigPage, self).save(no_messages=True, *args, **kwargs)
        result = self.form.callback_results.get("result")
        if result:
            messages.success(
                _(
                    "Configuration was successfully restored. "
                    "Note that a reboot will be required to apply restored "
                    "configuration."
                )
            )
        else:
            messages.warning(_("Failed to restore the backup from the provided file."))
        return result
