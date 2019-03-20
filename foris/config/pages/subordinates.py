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
import typing

from foris import fapi
from foris.config_handlers import subordinates, wifi
from foris.state import current_state
from foris.utils import messages
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, _

from .base import ConfigPageMixin, JoinedPages


class SubordinatesSetupPage(ConfigPageMixin, subordinates.SubordinatesConfigHandler):
    slug = "subordinates"
    menu_order = 1  # submenu

    template = "config/subordinates_setup"
    menu_title = gettext("Set up")
    userfriendly_title = gettext("Managed devices: Set up")
    template_type = "jinja2"

    def render(self, **kwargs):
        data = current_state.backend.perform("subordinates", "list")
        kwargs["subordinates"] = data["subordinates"]
        return super().render(**kwargs)

    def save(self, *args, **kwargs):
        super(SubordinatesSetupPage, self).save(no_messages=True, *args, **kwargs)
        data = self.form.callback_results
        if data["result"]:
            messages.success(_(
                "Token was successfully added and client '%(controller_id)s' "
                "should be visible in a moment."
            ) % dict(controller_id=data["controller_id"]))
        else:
            messages.error(_("Failed to add token."))

        return data["result"]

    def _check_and_get_controller_id(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="remote"))

        form = self.get_controller_id_form(bottle.request.POST.decode())
        if not form.data["controller_id"]:
            raise bottle.HTTPError(404, "controller_id not found")
        return form.data["controller_id"]

    def _ajax_list_subordinates(self):
        data = current_state.backend.perform("subordinates", "list")
        return bottle.template(
            "config/_subordinates_list_setup.html.j2",
            subordinates=data["subordinates"],
            template_adapter=bottle.Jinja2Template,
        )

    def _ajax_delete(self):
        controller_id = self._check_and_get_controller_id()
        res = current_state.backend.perform(
            "subordinates", "del", {"controller_id": controller_id})
        if res["result"]:
            return bottle.template(
                "config/_subordinates_message.html.j2",
                message={
                    "classes": ['success'],
                    "text": _("Subordinate '%(controller_id)s' was successfully deleted.")
                    % dict(controller_id=controller_id)
                },
                template_adapter=bottle.Jinja2Template,
            )
        else:
            return bottle.template(
                "config/_subordinates_message.html.j2",
                message={
                    "classes": ['error'],
                    "text": _("Failed to delete subordinate '%(controller_id)s'.")
                    % dict(controller_id=controller_id)
                },
                template_adapter=bottle.Jinja2Template,
            )

    def _ajax_set_enabled(self, enabled):
        controller_id = self._check_and_get_controller_id()
        res = current_state.backend.perform("subordinates", "set_enabled", {
            "controller_id": controller_id,
            "enabled": enabled,
        })
        if res["result"]:
            if enabled:
                message = {
                    "classes": ['success'],
                    "text": _("Subordinate '%(controller_id)s' was sucessfuly enabled.")
                    % dict(controller_id=controller_id)
                }
            else:
                message = {
                    "classes": ['success'],
                    "text": _("Subordinate '%(controller_id)s' was sucessfuly disabled.")
                    % dict(controller_id=controller_id)
                }
        else:
            if enabled:
                message = {
                    "classes": ['error'],
                    "text": _("Failed to enable subordinate '%(controller_id)s'.")
                    % dict(controller_id=controller_id)
                }
            else:
                message = {
                    "classes": ['error'],
                    "text": _("Failed to disable subordinate '%(controller_id)s'.")
                    % dict(controller_id=controller_id)
                }

        return bottle.template(
            "config/_subordinates_message.html.j2",
            message=message,
            template_adapter=bottle.Jinja2Template,
        )

    def call_ajax_action(self, action):
        if action == "list":
            return self._ajax_list_subordinates()
        elif action == "disable":
            return self._ajax_set_enabled(False)
        elif action == "enable":
            return self._ajax_set_enabled(True)
        elif action == "delete":
            return self._ajax_delete()
        raise ValueError("Unknown AJAX action.")

    @classmethod
    def is_visible(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_enabled_static(cls)

    def get_page_form(self, form_name: str, data: dict, controller_id: str) -> typing.Tuple[
            fapi.ForisAjaxForm, typing.Callable[[dict], typing.Tuple['str', 'str']]
    ]:
        """Returns appropriate foris form and handler to generate response
        """
        form: fapi.ForisAjaxForm
        if form_name == "sub-form":
            form = subordinates.SubordinatesEditForm(data)

            def prepare_message(results: dict) -> dict:
                if results["result"]:
                    message = {
                        "classes": ['success'],
                        "text": _("Device '%(controller_id)s' was sucessfully updated.")
                        % dict(controller_id=data["controller_id"])
                    }

                else:
                    message = {
                        "classes": ['error'],
                        "text": _("Failed to update subordinate '%(controller_id)s'.")
                        % dict(controller_id=data["controller_id"])
                    }
                return message

            form.url = reverse("config_ajax_form", page_name="subordinates", form_name="sub-form")
            return form, prepare_message

        elif form_name == "subsub-form":
            form = subordinates.SubsubordinatesEditForm(data)

            def prepare_message(results: dict) -> dict:
                if results["result"]:
                    message = {
                        "classes": ['success'],
                        "text": _("Subsubordinate '%(controller_id)s' was sucessfully updated.")
                        % dict(controller_id=data["controller_id"])
                    }

                else:
                    message = {
                        "classes": ['error'],
                        "text": _("Failed to update subsubordinate '%(controller_id)s'.")
                        % dict(controller_id=data["controller_id"])
                    }
                return message

            form.url = reverse(
                "config_ajax_form", page_name="subordinates", form_name="subsub-form")
            return form, prepare_message

        raise bottle.HTTPError(404, "No form '%s' not found." % form_name)


class SubordinatesWifiPage(ConfigPageMixin):
    slug = "subordinates-wifi"
    menu_order = 2  # submenu

    template = "config/subordinates_wifi"
    menu_title = gettext("Wi-Fi")
    userfriendly_title = gettext("Managed devices: Wi-Fi")
    template_type = "jinja2"

    def render(self, **kwargs):
        data = current_state.backend.perform("subordinates", "list")
        kwargs["subordinates"] = data["subordinates"]
        return super().render(**kwargs)

    @classmethod
    def is_visible(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_enabled_static(cls)

    def _ajax_list_subordinates(self):
        data = current_state.backend.perform("subordinates", "list")
        return bottle.template(
            "config/_subordinates_list_wifi.html.j2",
            subordinates=data["subordinates"],
            template_adapter=bottle.Jinja2Template,
        )

    def call_ajax_action(self, action):
        if action == "list":
            return self._ajax_list_subordinates()
        raise ValueError("Unknown AJAX action.")

    def get_page_form(self, form_name: str, data: dict, controller_id: str) -> typing.Tuple[
            fapi.ForisAjaxForm, typing.Callable[[dict], typing.Tuple['str', 'str']]
    ]:
        """Returns appropriate foris form and handler to generate response
        """
        if form_name == "wifi-form":
            form = wifi.WifiEditForm(data, controller_id=controller_id)

            def prepare_message(results: dict) -> dict:
                if results["result"]:
                    message = {
                        "classes": ['success'],
                        "text": _("Wifi settings was sucessfully updated.")
                    }

                else:
                    message = {
                        "classes": ['error'],
                        "text": _("Failed to update Wifi settings.")
                    }
                return message

            form.url = reverse("config_ajax_form", page_name="subordinates-wifi", form_name="wifi-form")
            return form, prepare_message

        raise bottle.HTTPError(404, "No form '%s' not found." % form_name)


class SubordinatesJoinedPage(JoinedPages):
    userfriendly_title = gettext("Managed devices")
    name = "subordinates-main"

    subpages: typing.Iterable[typing.Type['ConfigPageMixin']] = [
        SubordinatesSetupPage,
        SubordinatesWifiPage,
    ]

    @classmethod
    def is_visible(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_enabled_static(cls)
