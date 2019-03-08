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

import typing

from datetime import datetime
import base64
import logging
import time
import uuid

from bottle import Bottle, request, template, response, jinja2_template
from urllib.parse import urlencode
import bottle

from foris import fapi
from foris.common import login
from foris.guide import Workflow
from foris.utils.translators import gettext_dummy as gettext, _
from foris.config_handlers import (
    backups, dns, misc, notifications, wan, lan, updater, wifi, networks,
    guest, profile, remote, subordinates
)
from foris.utils import login_required, messages, is_safe_redirect
from foris.middleware.bottle_csrf import CSRFPlugin
from foris.utils.routing import reverse
from foris.state import current_state


logger = logging.getLogger(__name__)


class ConfigPageMixin(object):
    # page url part /config/<slug>
    slug: typing.Optional[str] = None
    menu_order = 50
    template = "config/main"
    template_type = "simple"

    def call_action(self, action):
        """Call config page action.

        :param action:
        :return: object that can be passed as HTTP response to Bottle
        """
        raise bottle.HTTPError(404, "No actions specified for this page.")

    def call_ajax_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        raise bottle.HTTPError(404, "No AJAX actions specified for this page.")

    def get_page_form(self, form_name: str, data: dict, controller_id: str) -> typing.Tuple[
            fapi.ForisAjaxForm, typing.Callable[[dict], typing.Tuple['str', 'str']]
    ]:
        """Returns appropriate foris form and handler to generate response
        """
        raise bottle.HTTPError(404, "No forms specified for this page.")

    def call_insecure(self, identifier):
        """Handels insecure request (no login required)

        :param namespace: namespace of the storage (e.g. tokens)
        :return: object that can be passed as HTTP response to Bottle
        """
        raise bottle.HTTPError(404, "No storage specified for this page.")

    def default_template(self, **kwargs):
        if self.template_type == "jinja2":
            page_template = "%s.html.j2" % self.template
            kwargs['template_adapter'] = bottle.Jinja2Template
        else:
            page_template = self.template
        return template(
            page_template, title=_(kwargs.pop('title', self.userfriendly_title)), **kwargs)

    def render(self, **kwargs):
        try:
            form = getattr(self, "form")
            first_section = form.sections[0]
            title = first_section.title
            description = first_section.description
        except (NotImplementedError, AttributeError):
            form = None
            title = self.userfriendly_title
            description = None

        return self.default_template(form=form, title=title, description=description, **kwargs)

    def save(self, *args, **kwargs):
        no_messages = kwargs.pop("no_messages", False)
        result = super(ConfigPageMixin, self).save(*args, **kwargs)
        if no_messages:
            return result
        if result:
            messages.success(_("Configuration was successfully saved."))
        else:
            messages.warning(_("There were some errors in your input."))
        return result

    @staticmethod
    def get_menu_tag_static(cls):
        if current_state.guide.enabled and current_state.guide.current == cls.slug:
            return {
                "show": True,
                "hint": "",
                "text": "<i class='fas fa-reply'></i>",
            }
        else:
            return {
                "show": False,
                "hint": "",
                "text": "",
            }

    @classmethod
    def get_menu_tag(cls):
        return ConfigPageMixin.get_menu_tag_static(cls)

    @staticmethod
    def is_visible_static(cls):
        if current_state.guide.enabled:
            return cls.slug in current_state.guide.steps

        return True

    @classmethod
    def is_visible(cls):
        return ConfigPageMixin.is_visible_static(cls)

    @staticmethod
    def is_enabled_static(cls):
        if current_state.guide.enabled:
            return cls.slug in current_state.guide.available_tabs

        return True

    @classmethod
    def is_enabled(cls):
        return ConfigPageMixin.is_enabled_static(cls)


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
        notification_ids = request.POST.getall("notification_ids[]")
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
            return template(
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


class PasswordConfigPage(ConfigPageMixin, misc.PasswordHandler):
    slug = "password"
    menu_order = 10
    template = "config/password"
    template_type = "jinja2"

    def __init__(self, *args, **kwargs):
        super(PasswordConfigPage, self).__init__(change=current_state.password_set, *args, **kwargs)

    def save(self, *args, **kwargs):
        result = super(PasswordConfigPage, self).save(no_messages=True, *args, **kwargs)
        wrong_old_password = self.form.callback_results.get('wrong_old_password', False)
        system_password_no_error = self.form.callback_results.get('system_password_no_error', None)
        foris_password_no_error = self.form.callback_results.get('foris_password_no_error', None)

        compromised = self.form.callback_results.get("compromised")
        if compromised:
            messages.error(
                _(
                    "The password you've entered has been compromised. "
                    "It appears %(count)d times in '%(list)s' list."
                ) % dict(count=compromised['count'], list=compromised['list'])
            )
            return result

        if wrong_old_password:
            messages.error(_("Old password you entered was not valid."))
            return result

        if system_password_no_error is not None:
            if system_password_no_error:
                messages.success(_("System password was successfully saved."))
            else:
                messages.error(_("Failed to save system password."))
        if foris_password_no_error is not None:
            if foris_password_no_error:
                messages.success(_("Foris password was successfully saved."))
            else:
                messages.error(_("Failed to save Foris password."))

        return result


class RemoteConfigPage(ConfigPageMixin, remote.RemoteHandler):
    slug = "remote"

    menu_order = 11

    TOKEN_LINK_EXPIRATION = 30
    token_links = {}

    template = "config/remote"
    userfriendly_title = gettext("Remote Access")
    template_type = "jinja2"

    @classmethod
    def token_cleanup(cls):
        now = time.time()
        cls.token_links = {k: v for k, v in cls.token_links.items() if now <= v["expiration"]}

    def render(self, **kwargs):
        data = current_state.backend.perform("remote", "get_status")

        kwargs["status"] = data["status"]
        kwargs["tokens"] = data["tokens"]
        kwargs["backend_data"] = self.backend_data

        kwargs["revoke_token_form"] = self.get_token_id_form()
        kwargs["generate_token_form"] = self.get_generate_token_form()
        kwargs["download_token_form"] = self.get_token_id_form()

        return super().render(**kwargs)

    def save(self, *args, **kwargs):
        kwargs["no_messages"] = True
        result = super().save(*args, **kwargs)
        if self.form.callback_results["enabled"]:
            if self.form.callback_results["result"]:
                messages.success(_("Remote access was sucessfully enabled."))
            else:
                messages.error(
                    _(
                        "Failed to enable the remote access. You are probably using "
                        "a message bus which doesn't support the remote access or "
                        "the CA for remote access hasn't been generated yet."
                    )
                )
        else:
            if self.form.callback_results["result"]:
                messages.success(_("Remote access was sucessfully disabled."))
            else:
                messages.error(_("Failed to disable remote access."))

        return result

    def _check_post(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="remote"))

    def _ajax_list_tokens(self):
        data = current_state.backend.perform("remote", "get_status")
        return template(
            "config/_remote_tokens.html.j2",
            tokens=data["tokens"],
            template_adapter=bottle.Jinja2Template,
        )

    def _ajax_revoke_token(self):
        self._check_post()
        form = self.get_token_id_form(bottle.request.POST.decode())
        if not form.data["token_id"]:
            raise bottle.HTTPError(404, "token_id not found")

        bottle.response.set_header("Content-Type", "application/json")
        return current_state.backend.perform(
            "remote", "revoke", {"id": form.data["token_id"]})

    def _ajax_generate_token(self):
        self._check_post()
        form = self.get_generate_token_form(bottle.request.POST.decode())
        if not form.data["name"]:
            raise bottle.HTTPError(404, "name not found")

        bottle.response.set_header("Content-Type", "application/json")
        return current_state.backend.perform(
            "remote", "generate_token", {"name": form.data["name"]})

    def _ajax_prepare_token(self):
        self._check_post()
        RemoteConfigPage.token_cleanup()

        form = self.get_token_id_form(bottle.request.POST.decode())
        token_id = form.data.get("token_id")
        if not token_id:
            raise bottle.HTTPError(404, "id not found")
        name = form.data.get("name", token_id)

        res = current_state.backend.perform("remote", "get_token", {"id": form.data["token_id"]})
        if res["status"] != "valid":
            raise bottle.HTTPError(404, "token not found")

        bottle.response.set_header("Content-Type", "application/json")
        new_uuid = uuid.uuid4()
        RemoteConfigPage.token_links[str(new_uuid)] = {
            "expiration": time.time() + RemoteConfigPage.TOKEN_LINK_EXPIRATION,
            "name": name,
            "token": base64.b64decode(res["token"]),
        }

        return {
            "url": reverse("config_insecure", page_name="remote", identifier=str(new_uuid)),
            "expires_in": RemoteConfigPage.TOKEN_LINK_EXPIRATION,
        }

    def call_ajax_action(self, action):
        if action == "generate-token":
            return self._ajax_generate_token()
        elif action == "revoke-token":
            return self._ajax_revoke_token()
        elif action == "list-tokens":
            return self._ajax_list_tokens()
        elif action == "prepare-token":
            return self._ajax_prepare_token()

        raise ValueError("Unknown AJAX action.")

    def _action_generate_ca(self):
        self._check_post()
        messages.info(_("Starting to generate CA for remote access."))
        current_state.backend.perform("remote", "generate_ca")
        # don't need to handle async_id (should influence all clients)
        bottle.redirect(reverse("config_page", page_name="remote"))

    def _action_delete_ca(self):
        self._check_post()
        data = current_state.backend.perform("remote", "delete_ca")
        if data["result"]:
            messages.success(_("CA for remote access was sucessfully deleted."))
        else:
            messages.error(_("Failed to delete CA for remote access."))
        bottle.redirect(reverse("config_page", page_name="remote"))

    def call_insecure(self, identifier):
        RemoteConfigPage.token_cleanup()

        try:
            record = RemoteConfigPage.token_links[identifier]
        except KeyError:
            raise bottle.HTTPError(404, "token url doesn't exists")

        bottle.response.set_header("Content-Type", "application/x-gzip")
        bottle.response.set_header(
            "Content-Disposition", 'attachment; filename="token-%s.tar.gz"' % record["name"]
        )
        bottle.response.set_header("Content-Length", len(record["token"]))
        return record["token"]

    def call_action(self, action):
        if action == "generate-ca":
            self._action_generate_ca()
        elif action == "delete-ca":
            self._action_delete_ca()
        elif action == "download-token":
            self._action_download_token()

        raise ValueError("Unknown action.")

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


class SubordinatesConfigPage(ConfigPageMixin, subordinates.SubordinatesConfigHandler):
    slug = "subordinates"
    menu_order = 12

    template = "config/subordinates"
    userfriendly_title = gettext("Subordinates")
    template_type = "jinja2"

    def render(self, **kwargs):
        data = current_state.backend.perform("subordinates", "list")

        kwargs["subordinates"] = data["subordinates"]

        return super().render(**kwargs)

    def save(self, *args, **kwargs):
        super(SubordinatesConfigPage, self).save(no_messages=True, *args, **kwargs)
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
        view = bottle.request.GET.decode().get("view")
        return template(
            "config/_subordinates_list.html.j2",
            subordinates=data["subordinates"],
            view = view,
            template_adapter=bottle.Jinja2Template,
        )

    def _ajax_delete(self):
        controller_id = self._check_and_get_controller_id()
        res = current_state.backend.perform(
            "subordinates", "del", {"controller_id": controller_id})
        if res["result"]:
            return template(
                "config/_subordinates_message.html.j2",
                message={
                    "classes": ['success'],
                    "text": _("Subordinate '%(controller_id)s' was successfully deleted.")
                    % dict(controller_id=controller_id)
                },
                template_adapter=bottle.Jinja2Template,
            )
        else:
            return template(
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

        return template(
            "config/_subordinates_message.html.j2",
            message=message,
            template_adapter=bottle.Jinja2Template,
        )

    def _ajax_update_sub(self):
        controller_id = self._check_and_get_controller_id()
        form = self.get_subordinate_update_form(bottle.request.POST.decode())
        form.save()
        if form.callback_results["result"]:
            message = {
                "classes": ['success'],
                "text": _("Subordinate '%(controller_id)s' was sucessfully updated.")
                % dict(controller_id=controller_id)
            }

        else:
            message = {
                "classes": ['error'],
                "text": _("Failed to update subordinate '%(controller_id)s'.")
                % dict(controller_id=controller_id)
            }

        res = template(
            "config/_subordinates_message.html.j2",
            message=message,
            dom_id="edit-form-message",
            template_adapter=bottle.Jinja2Template,
        )
        return res

    def _ajax_update_subsub(self):
        controller_id = self._check_and_get_controller_id()
        form = self.get_subsubordinate_update_form(bottle.request.POST.decode())
        form.save()
        if form.callback_results["result"]:
            message = {
                "classes": ['success'],
                "text": _("Subsubordinate '%(controller_id)s' was sucessfully updated.")
                % dict(controller_id=controller_id)
            }

        else:
            message = {
                "classes": ['error'],
                "text": _("Failed to update subsubordinate '%(controller_id)s'.")
                % dict(controller_id=controller_id)
            }

        return template(
            "config/_subordinates_message.html.j2",
            message=message,
            dom_id="edit-form-message",
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
        elif action == "update_sub":
            return self._ajax_update_sub()
        elif action == "update_subsub":
            return self._ajax_update_subsub()
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
                        "text": _("Subordinate '%(controller_id)s' was sucessfully updated.")
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

        elif form_name == "wifi-form":
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

            form.url = reverse("config_ajax_form", page_name="subordinates", form_name="wifi-form")
            return form, prepare_message

        raise bottle.HTTPError(404, "No form '%s' not found." % form_name)


class ProfileConfigPage(ConfigPageMixin, profile.ProfileHandler):
    slug = "profile"
    menu_order = 13
    template = "config/profile"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs['workflows'] = [
            Workflow(
                e, self.backend_data["current_workflow"] == e,
                self.backend_data["recommended_workflow"] == e
            ) for e in self.backend_data["available_workflows"]
        ]

        # perform some workflow sorting
        SCORE = {
            "router": 1,  # router first
            "bridge": 2,
        }
        kwargs['workflows'].sort(key=lambda e: (SCORE.get(e.name, 99), e.name))
        return super(ProfileConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        result = super(ProfileConfigPage, self).save(no_messages=True, *args, **kwargs)
        if self.form.callback_results["result"]:
            messages.success(_("Guide workflow was sucessfully set."))
        else:
            messages.error(_("Failed to set guide workflow."))
        return result

    @classmethod
    def is_visible(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_enabled_static(cls)


class NetworksConfigPage(ConfigPageMixin, networks.NetworksHandler):
    slug = "networks"
    menu_order = 14
    template = "config/networks"
    template_type = "jinja2"

    def render(self, **kwargs):
        # place non-configurable intefaces in front of configurable
        kwargs['networks'] = {}
        for network_name in self.backend_data["networks"].keys():
            kwargs['networks'][network_name] = sorted(
                self.backend_data["networks"][network_name],
                key=lambda x: (1 if x["configurable"] else 0, x["slot"]), reverse=False
            )
            for network in kwargs['networks'][network_name]:
                if network["type"] == "wifi":
                    network["slot"] = network["bus"] + network["slot"]

        # don't display inconfigurable devices in none network (can't be configured anyway)
        kwargs['networks']['none'] = [
            e for e in kwargs['networks']['none'] if e["configurable"]
        ]

        return super(NetworksConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        result = super(NetworksConfigPage, self).save(no_messages=True, *args, **kwargs)
        if self.form.callback_results["result"]:
            messages.success(_("Network configuration was sucessfully updated."))
        else:
            messages.error(_("Unable to update your network configuration."))
        return result

    @classmethod
    def is_enabled(cls):
        if current_state.device in ["turris"]:
            return False
        # Don't show in turrisOS version < "4.0"
        if int(current_state.turris_os_version.split(".", 1)[0]) < 4:
            return False
        return ConfigPageMixin.is_enabled_static(cls)

    @classmethod
    def is_visible(cls):
        return cls.is_enabled()


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


class LanConfigPage(ConfigPageMixin, lan.LanHandler):
    slug = "lan"
    menu_order = 16

    template = "config/lan"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs["dhcp_clients"] = self.backend_data["mode_managed"]["dhcp"]["clients"]
        kwargs["interface_count"] = self.backend_data["interface_count"]
        kwargs["interface_up_count"] = self.backend_data["interface_up_count"]
        for client in kwargs["dhcp_clients"]:
            client["expires"] = datetime.utcfromtimestamp(client["expires"]).strftime(
                "%Y-%m-%d %H:%M"
            )

        return super(LanConfigPage, self).render(**kwargs)


class GuestConfigPage(ConfigPageMixin, guest.GuestHandler):
    slug = "guest"
    menu_order = 17

    template = "config/guest"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs["dhcp_clients"] = self.backend_data["dhcp"]["clients"]
        kwargs["interface_count"] = self.backend_data["interface_count"]
        kwargs["interface_up_count"] = self.backend_data["interface_up_count"]
        for client in kwargs["dhcp_clients"]:
            client["expires"] = datetime.utcfromtimestamp(client["expires"]).strftime(
                "%Y-%m-%d %H:%M"
            )

        return super(GuestConfigPage, self).render(**kwargs)


class TimeConfigPage(ConfigPageMixin, misc.UnifiedTimeHandler):
    """ Timezone / Time configuration """
    slug = "time"
    menu_order = 18

    template = "config/time"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs["ntp_servers"] = self.backend_data["time_settings"]["ntp_servers"]
        return super().render(**kwargs)

    def call_ajax_action(self, action):
        if action == "ntpdate-trigger":
            return current_state.backend.perform("time", "ntpdate_trigger")
        raise ValueError("Unknown AJAX action.")


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


class WifiConfigPage(ConfigPageMixin, wifi.WifiHandler):
    slug = "wifi"
    menu_order = 20

    template = "config/wifi"
    template_type = "jinja2"

    def _action_reset(self):

        if bottle.request.method != 'POST':
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
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        handler = notifications.NotificationsHandler(request.POST.decode())
        if handler.save():
            messages.success(_("Configuration was successfully saved."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        messages.warning(_("There were some errors in your input."))
        return super(MaintenanceConfigPage, self).render(notifications_form=handler.form)

    def _action_test_notifications(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        data = current_state.backend.perform(
            "router_notifications", "create",
            {
                "msg": "_(This is a testing notification. Please ignore me.)",
                "severity": "news",
                "immediate": True,
            }
        )

        if data["result"]:
            messages.success(_("Testing message was sent, please check your inbox."))
        else:
            messages.error(_(
                "Sending of the testing message failed, your configuration is possibly wrong."
            ))
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
            notifications_form=notifications_handler.form,
            **kwargs
        )

    def save(self, *args, **kwargs):
        super(MaintenanceConfigPage, self).save(no_messages=True, *args, **kwargs)
        result = self.form.callback_results.get('result')
        if result:
            messages.success(_("Configuration was successfully restored. "
                               "Note that a reboot will be required to apply restored "
                               "configuration."))
        else:
            messages.warning(_("Failed to restore the backup from the provided file."))
        return result


class UpdaterConfigPage(ConfigPageMixin, updater.UpdaterHandler):
    slug = "updater"
    menu_order = 22

    template = "config/updater"
    template_type = "jinja2"

    def _action_resolve_approval(self):
        if bottle.request.method != 'POST':
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
            "updater", "resolve_approval", {"hash": approval_id, "solution": solution})

    def call_ajax_action(self, action):
        if action == "resolve_approval":
            return self._action_resolve_approval()
        raise ValueError("Unknown action.")

    def render(self, **kwargs):
        kwargs['is_updater_enabled'] = lambda: self.updater_enabled
        kwargs['agreed_collect'] = self.agreed_collect
        kwargs['current_approval'] = self.current_approval
        kwargs['get_approval_setting_status'] = lambda: self.approval_setting_status
        kwargs['get_approval_setting_delay'] = lambda: self.approval_setting_delay
        if kwargs['current_approval']['present']:
            kwargs['current_approval']['time'] = datetime.strptime(
                kwargs['current_approval']['time'].split(".", 1)[0], "%Y-%m-%dT%H:%M:%S")

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
            messages.success(_("Configuration was successfully saved. Selected "
                               "packages should be installed or removed shortly."))
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


class GuideFinishedPage(ConfigPageMixin, misc.GuideFinishedHandler):
    slug = "finished"
    menu_order = 90

    template_type = "jinja2"
    template = "config/finished"

    def save(self, *args, **kwargs):
        result = super().save(no_messages=True, *args, **kwargs)
        if not self.form.callback_results["result"]:
            messages.error(_("Failed to finish the guide."))
        return result

    @classmethod
    def is_visible(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_enabled_static(cls)


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


config_pages = {
    e.slug: e for e in [
        NotificationsConfigPage,
        RemoteConfigPage,
        SubordinatesConfigPage,
        PasswordConfigPage,
        ProfileConfigPage,
        NetworksConfigPage,
        WanConfigPage,
        TimeConfigPage,
        DNSConfigPage,
        LanConfigPage,
        GuestConfigPage,
        WifiConfigPage,
        MaintenanceConfigPage,
        UpdaterConfigPage,
        GuideFinishedPage,
        AboutConfigPage,
    ]
}


def get_config_pages():
    """ Returns sorted config pages
    """
    res = sorted(config_pages.values(), key=lambda e: (e.menu_order, e.slug))
    return res


def add_config_page(page_class):
    """Register config page in /config/ URL namespace.

    :param page_class: handler class
    """
    if page_class.slug is None:
        raise Exception("Page %s doesn't define a propper slug" % page_class)
    if page_class.slug in config_pages:
        raise Exception("Error when adding page %s slug '%s' is already used in %s" % (
            page_class, page_class.slug, config_pages[page_class.slug]
        ))
    config_pages[page_class.slug] = page_class


def get_config_page(page_name):
    ConfigPage = config_pages.get(page_name, None)
    if ConfigPage is None:
        raise bottle.HTTPError(404, "Unknown configuration page.")
    return ConfigPage


def _redirect_to_default_location():

    next_page = "notifications"
    # by default redirect to current guide step
    if current_state.guide.enabled:
        next_page = current_state.guide.current if current_state.guide.current else next_page

    bottle.redirect(reverse("config_page", page_name=next_page))


@login_required
def index():
    _redirect_to_default_location()


@login_required
def config_page_get(page_name):
    # redirect in case that guide is not passed
    if current_state.guide.enabled and page_name not in current_state.guide.available_tabs:
        bottle.redirect(reverse("config_page", page_name=current_state.guide.current))

    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)

    # test if page is enabled otherwise redirect to default
    if not ConfigPage.is_enabled() or not ConfigPage.is_visible():
        _redirect_to_default_location()

    config_page = ConfigPage()
    return config_page.render(active_config_page_key=page_name)


@login_required
def config_page_post(page_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.POST.decode())
    if request.is_xhr:
        if request.POST.pop("_update", None):
            # if update was requested, just render the page - otherwise handle actions as usual
            pass
        else:
            config_page.save()
        return config_page.render(is_xhr=True)
    try:
        if config_page.save():
            bottle.redirect(request.fullpath)
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        messages.error(_("Configuration could not be saved due to an internal error."))
        logger.exception("Error when saving form.")
    logger.warning("Form not saved.")
    return config_page.render(active_config_page_key=page_name)


@login_required
def config_action(page_name, action):
    bottle.SimpleTemplate.defaults['active_config_page'] = page_name
    bottle.Jinja2Template.defaults['active_config_page'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    try:
        result = config_page.call_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")


@login_required
def config_action_post(page_name, action):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.POST.decode())
    if request.is_xhr:
        if request.POST.pop("_update", None):
            # if update was requested, just render the page - otherwise handle actions as usual
            return config_page.render(is_xhr=True)
    # check if the button click wasn't any sub-action
    subaction = request.POST.pop("action", None)
    if subaction:
        return config_action_post(page_name, subaction)
    try:
        result = config_page.call_action(action)
        try:
            if not result:
                bottle.redirect(reverse("config_page", page_name=page_name))
        except TypeError:
            # raised by Validator - could happen when the form is posted with wrong fields
            messages.error(_("Configuration could not be saved due to an internal error."))
            logger.exception("Error when saving form.")
        logger.warning("Form not saved.")
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")


@login_required
def config_ajax(page_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    action = request.params.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    try:
        result = config_page.call_ajax_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")


@login_required
def config_ajax_form(page_name, form_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    if not request.is_xhr:
        raise bottle.HTTPError(400, "Should be ajax request")
    try:
        trigger = request.POST.pop("_update", None) is None
        hide = request.POST.pop("_hide", False)

        controller_id = request.POST.pop("_controller_id", None)
        form, response_handler = config_page.get_page_form(
            form_name, request.POST.decode(), controller_id
        )

        message = None
        if form.foris_form.validate() and trigger:
            form.foris_form.save()
            message = response_handler(form.foris_form.callback_results)

        return template(
            form.template_name,
            message=message,
            hide=hide,
            form=form.foris_form,
            ajax_form=form,
            template_adapter=bottle.Jinja2Template,
        )
    except (ValueError, KeyError):
        raise bottle.HTTPError(404, "Form not found.")
    raise bottle.HTTPError(404, "Form not found.")


def config_insecure(page_name, identifier):
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.GET.decode())
    try:
        return config_page.call_insecure(identifier)
    except ValueError:
        raise bottle.HTTPError(404, "Unknown Insecure link")


def init_app():
    app = Bottle()
    app.install(CSRFPlugin())
    app.route("/", name="config_index", callback=index)
    app.route("/<page_name:re:.+>/ajax", name="config_ajax", method=("GET", "POST"),
              callback=config_ajax)
    app.route("/<page_name:re:.+>/ajax/form/<form_name:re:.+>", name="config_ajax_form", method=("POST"),
              callback=config_ajax_form)
    app.route("/<page_name:re:.+>/action/<action:re:.+>", method="POST",
              callback=config_action_post)
    app.route("/<page_name:re:.+>/action/<action:re:.+>", name="config_action",
              callback=config_action)
    app.route("/<page_name:re:.+>/insecure/<identifier:re:[0-9a-zA-Z-]+>",
              name="config_insecure", callback=config_insecure)
    app.route("/<page_name:re:.+>/", method="POST",
              callback=config_page_post)
    app.route("/<page_name:re:.+>/", name="config_page",
              callback=config_page_get)
    bottle.SimpleTemplate.defaults['get_config_pages'] = get_config_pages
    bottle.Jinja2Template.defaults['get_config_pages'] = get_config_pages
    return app


def login_redirect():
    next_url = bottle.request.GET.get("next")
    if next_url and is_safe_redirect(next_url, bottle.request.get_header('host')):
        bottle.redirect(next_url)
    bottle.redirect(reverse("config_index"))


@bottle.jinja2_view("index.html.j2")
def top_index():
    session = bottle.request.environ['foris.session']
    if bottle.request.method == 'POST':
        next = bottle.request.POST.get("next", None)
        login(next, session)
        # if login passes it will redirect to a proper page
        # otherwise it contains next parameter
        messages.error(_("The password you entered was not valid."))
        response.status = 403
    else:
        next = bottle.request.GET.get("next", None)
        if not current_state.password_set:  # auto login if no password is set
            if session.is_anonymous:
                session.recreate()
            session["user_authenticated"] = True
            session.save()

        if session.get("user_authenticated"):
            login_redirect()

    return dict(
        luci_path="//%(host)s/%(path)s"
        % {'host': bottle.request.get_header('host'), 'path': 'cgi-bin/luci'},
        next=next
    )
