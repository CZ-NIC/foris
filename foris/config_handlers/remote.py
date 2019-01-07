# Foris - web administration interface for OpenWrt
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


from .base import BaseConfigHandler

from foris import fapi

from foris.form import Checkbox, Number, Textbox
from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, _
from foris.validators import InRange, LenRange, RegExp


class RemoteHandler(BaseConfigHandler):

    # Translate status obtained via get_status
    CLIENT_STATUS_VALID = gettext("valid")
    CLIENT_STATUS_REVOKED = gettext("revoked")
    CLIENT_STATUS_EXPIRED = gettext("expired")
    CLIENT_STATUS_GENERATING = gettext("generating")
    CLIENT_STATUS_LOST = gettext("lost")

    TRANSLATION_MAP = {
        "valid": CLIENT_STATUS_VALID,
        "revoked": CLIENT_STATUS_REVOKED,
        "expired": CLIENT_STATUS_EXPIRED,
        "generating": CLIENT_STATUS_GENERATING,
        "lost": CLIENT_STATUS_LOST,
    }

    userfriendly_title = gettext("Remote Access")

    def __init__(self, *args, **kwargs):
        self.backend_data = current_state.backend.perform("remote", "get_settings")
        super().__init__(*args, **kwargs)

    def get_form(self):
        data = {
            "enabled": self.backend_data["enabled"],
            "port": self.backend_data["port"],
            "wan_access": self.backend_data["wan_access"],
        }

        if self.data:
            # Update from post
            data.update(self.data)

        form = fapi.ForisForm("remote", data)
        config_section = form.add_section(name="set_remote", title=_(self.userfriendly_title))
        config_section.add_field(
            Checkbox, name="enabled", label=_("Enable remote access"),
        )
        config_section.add_field(
            Checkbox, name="wan_access", label=_("Accessible via WAN"),
            hint=_(
                "If this option is check the device in the WAN network will be able to connect "
                "to the configuration interface. Otherwise only devices on LAN will be able to "
                "access the configuration interface."
            ),
        ).requires("enabled", True)
        config_section.add_field(
            Number, name="port", label=_("Port"),
            hint=_(
                "A port which will be opened for the remote configuration "
                "of this device."
            ),
            validator=[InRange(1, 2 ** 16 - 1)],
            default=11884,
        ).requires("enabled", True)

        def form_callback(data):
            msg = {"enabled": data['enabled']}

            if msg["enabled"]:
                msg["port"] = int(data["port"])
                msg["wan_access"] = data['wan_access']

            res = current_state.backend.perform("remote", "update_settings", msg)
            res['enabled'] = msg['enabled']

            return "save_result", res  # store {"result": ...} to be used later...

        form.add_callback(form_callback)
        return form

    def get_generate_token_form(self, data=None):
        generate_token_form = fapi.ForisForm("generate_remote_token", data)
        token_section = generate_token_form.add_section("generate_token", title=None)
        token_section.add_field(
            Textbox, name="name", label=_("Token name"), required=True,
            hint=_("The display name for the token. It must be shorter than 64 characters "
                   "and must contain only alphanumeric characters, dots, dashes and "
                   "underscores."),
            validators=[
                RegExp(_("Token name is invalid."), r'[a-zA-Z0-9_.-]+'), LenRange(1, 63)]
        )
        return generate_token_form

    def get_token_id_form(self, data=None):
        token_id_form = fapi.ForisForm("token_id_form", data)
        token_section = token_id_form.add_section("token_id_section", title=None)
        token_section.add_field(
            Textbox, name="token_id", label="", required=True,
            validators=[
                RegExp(_("Token id is invalid."), r'([a-zA-Z0-9][a-zA-Z0-9])+')]
        )
        token_section.add_field(
            Textbox, name="name", label=_("Token name"), required=False,
            validators=[
                RegExp(_("Token name is invalid."), r'[a-zA-Z0-9_.-]+'), LenRange(1, 63)],
        )
        return token_id_form
