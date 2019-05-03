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

from datetime import datetime

from foris.config_handlers import updater
from foris.state import current_state
from foris.utils import messages
from foris.utils.translators import _


from .base import ConfigPageMixin


class UpdaterConfigPage(ConfigPageMixin, updater.UpdaterHandler):
    slug = "updater"
    menu_order = 22

    template = "config/updater"
    template_type = "jinja2"

    def _action_resolve_approval(self):
        if bottle.request.method != "POST":
            raise bottle.HTTPError(405, "Method not allowed.")
        try:
            approval_id = bottle.request.POST.get("approval_id")
        except KeyError:
            raise bottle.HTTPError(400, "approval is missing.")

        try:
            solution = bottle.request.POST.get("solution").strip()
        except KeyError:
            raise bottle.HTTPError(400, "solution is missing.")

        if solution not in ("grant", "deny"):
            raise bottle.HTTPError(400, "wrong solution value (expected 'grant' or 'deny').")

        bottle.response.set_header("Content-Type", "application/json")
        return current_state.backend.perform(
            "updater", "resolve_approval", {"hash": approval_id, "solution": solution}
        )

    def call_ajax_action(self, action):
        if action == "resolve_approval":
            return self._action_resolve_approval()
        raise ValueError("Unknown action.")

    def render(self, **kwargs):
        kwargs["is_updater_enabled"] = lambda: self.updater_enabled
        kwargs["always_on_reasons"] = self.always_on_reasons
        kwargs["current_approval"] = self.current_approval
        kwargs["get_approval_setting_status"] = lambda: self.approval_setting_status
        kwargs["get_approval_setting_delay"] = lambda: self.approval_setting_delay
        if kwargs["current_approval"]["present"]:
            kwargs["current_approval"]["time"] = datetime.strptime(
                kwargs["current_approval"]["time"].split(".", 1)[0], "%Y-%m-%dT%H:%M:%S"
            )

        return super(UpdaterConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        result = super(UpdaterConfigPage, self).save(no_messages=True, *args, **kwargs)

        target = self.form.callback_results.get("target", None)
        if target in ["deny", "grant"]:
            result = self.form.callback_results["result"]
            if result:
                if target == "grant":
                    messages.success(_("Update was approved."))
                elif target == "deny":
                    messages.success(_("Update was postponed."))
            else:
                if target == "grant":
                    messages.error(_("Failed to approve the update."))
                elif target == "deny":
                    messages.error(_("Failed to postpone the update."))
            return result

        if result:
            messages.success(
                _(
                    "Configuration was successfully saved. Selected "
                    "packages should be installed or removed shortly."
                )
            )
        else:
            messages.warning(_("There were some errors in your input."))
        return result

    @classmethod
    def get_menu_tag(cls):
        if current_state.updater_is_running:
            return {
                "show": current_state.updater_is_running,
                "hint": _("Updater is running"),
                "text": u"<i class='fas fa-sync rotate'></i>",
            }
        else:
            return ConfigPageMixin.get_menu_tag_static(cls)
