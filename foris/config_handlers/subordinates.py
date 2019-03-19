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

import base64
import bottle
import typing

from foris import fapi
from foris.form import File, Hidden, Textbox
from foris.state import current_state
from foris.utils.translators import (
    gettext_dummy as gettext,
    gettext as _,
)

from .base import BaseConfigHandler
from .wifi import WifiEditForm


class SubordinatesConfigHandler(BaseConfigHandler):

    def get_form(self):
        form = fapi.ForisForm("suboridinates", self.data)

        section = form.add_section(
            name="main_section",
            title=_(self.userfriendly_title),
        )

        section.add_field(
            File, name="token_file", label=_("Token file"), required=True)

        def form_cb(data):
            res = current_state.backend.perform(
                "subordinates", "add_sub",
                {"token": base64.b64encode(data["token_file"].file.read()).decode("utf-8")}
            )

            return "save_result", res

        form.add_callback(form_cb)
        return form

    def get_controller_id_form(self, data=None):
        controller_id_form = fapi.ForisForm("controller_id_form", data)
        controller_section = controller_id_form.add_section("controller_section", title=None)
        controller_section.add_field(
            Hidden, name="controller_id", label="", required=True,
        )
        return controller_id_form


class SubordinatesEditForm(fapi.ForisAjaxForm):
    template_name = "config/_subordinates_edit.html.j2"

    def __init__(self, data, controller_id=None):
        self.subordinate_controller_id = data["controller_id"]
        super().__init__(data, controller_id)
        self.title = _("Edit device '%(controller_id)s'") % dict(
            controller_id=data["controller_id"])

    def convert_data_from_backend_to_form(self, backend_data):
        subordinates_list = backend_data["subordinates"]
        subordinates_map = {e["controller_id"]: e for e in subordinates_list}
        sub_record = subordinates_map.get(self.subordinate_controller_id, None)
        if not sub_record:
            raise bottle.HTTPError(
                404, f"Controller id {self.subordinate_controller_id} not found."
            )
        return sub_record["options"]

    def convert_data_from_form_to_backend(self, data):
        controller_id = data.pop("controller_id")
        return {
            "controller_id": controller_id,
            "options": data
        }

    def make_form(self, data: typing.Optional[dict]):

        form_data = self.convert_data_from_backend_to_form(
            current_state.backend.perform("subordinates", "list")
        )

        if data:
            form_data.update(data)

        sub_form = fapi.ForisForm("update_sub", form_data)
        sub_section = sub_form.add_section(
            "subordinate_section", title="", description=_(
                "You can edit managed devices here. These managed devices are directly connected to this "
                "device."
            )
        )
        sub_section.add_field(
            Textbox, name="custom_name", label=_("Custom Name"),
            hint=_("Nicer name for your device '%(controller_id)s'.")
            % dict(controller_id=data["controller_id"])
        )
        sub_section.add_field(
            Hidden, name="controller_id", required=True, title="",
        )

        def form_cb(data):
            msg_data = self.convert_data_from_form_to_backend(data)
            res = current_state.backend.perform("subordinates", "update_sub", msg_data)
            return "save_result", res
        sub_form.add_callback(form_cb)

        return sub_form


class SubsubordinatesEditForm(fapi.ForisAjaxForm):
    template_name = "config/_subordinates_edit.html.j2"

    def __init__(self, data, controller_id=None):
        self.subsubordinate_controller_id = data["controller_id"]
        super().__init__(data, controller_id)
        self.title = _("Edit managed device '%(controller_id)s'") % dict(
            controller_id=data["controller_id"])

    def convert_data_from_backend_to_form(self, backend_data):
        subordinates_list = backend_data["subordinates"]
        subsubordinates_map = {
            e["controller_id"]: e
            for record in subordinates_list
            for e in record["subsubordinates"]
        }
        subsub_record = subsubordinates_map.get(self.subsubordinate_controller_id, None)
        if not subsub_record:
            raise bottle.HTTPError(
                404, f"Controller id {self.subsubordinate_controller_id} not found."
            )
        return subsub_record["options"]

    def convert_data_from_form_to_backend(self, data):
        controller_id = data.pop("controller_id")
        return {
            "controller_id": controller_id,
            "options": data
        }

    def make_form(self, data: typing.Optional[dict]):

        form_data = self.convert_data_from_backend_to_form(
            current_state.backend.perform("subordinates", "list")
        )

        if data:
            form_data.update(data)

        sub_form = fapi.ForisForm("update_subsub", form_data)
        sub_section = sub_form.add_section(
            "subsubordinate_section", title="", description=_(
                "You can edit managed devices here. These devices are not "
                "not directly connected to this device but "
                "they are connected through another managed device."
            )
        )
        sub_section.add_field(
            Hidden, name="controller_id", required=True, title="",
        )
        sub_section.add_field(
            Textbox, name="custom_name", label=_("Custom Name"),
            hint=_("Nicer name for your device with serial '%(controller_id)s'.")
            % dict(controller_id=self.subsubordinate_controller_id)
        )

        def form_cb(data):
            res = current_state.backend.perform(
                "subordinates", "update_subsub",
                {
                    "controller_id": data["controller_id"],
                    "options": {"custom_name": data["custom_name"]}
                }
            )
            return "save_result", res
        sub_form.add_callback(form_cb)

        return sub_form


class SubordinatesWifiHandler(BaseConfigHandler):

    def get_form(self):
        ajax_form = WifiEditForm(self.data)
        return ajax_form.foris_form
