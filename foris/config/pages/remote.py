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

import base64
import bottle
import typing
import time
import uuid

from foris.config_handlers import remote
from foris.state import current_state
from foris.utils import messages
from foris.utils.translators import gettext_dummy as gettext, _
from foris.utils.routing import reverse

from .base import ConfigPageMixin


class RemoteConfigPage(ConfigPageMixin, remote.RemoteHandler):
    slug = "remote"

    menu_order = 11

    TOKEN_LINK_EXPIRATION = 30
    token_links: typing.Dict[str, typing.Any] = {}

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
        if bottle.request.method != "POST":
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="remote"))

    def _ajax_list_tokens(self):
        data = current_state.backend.perform("remote", "get_status")
        return bottle.template(
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
        return current_state.backend.perform("remote", "revoke", {"id": form.data["token_id"]})

    def _ajax_generate_token(self):
        self._check_post()
        form = self.get_generate_token_form(bottle.request.POST.decode())
        if not form.data["name"]:
            raise bottle.HTTPError(404, "name not found")

        bottle.response.set_header("Content-Type", "application/json")
        return current_state.backend.perform(
            "remote", "generate_token", {"name": form.data["name"]}
        )

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
