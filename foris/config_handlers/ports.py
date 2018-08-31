# coding=utf-8

# Foris - web administration interface
# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

from foris.utils.translators import gettext_dummy as gettext, _
from foris.form import MultiCheckbox


class PortsHandler(BaseConfigHandler):
    """ Ports settings handler
    """
    userfriendly_title = gettext("Ports")

    def load_backend_data(self):
        # data = current_state.backend.perform("dns", "get_settings")
        # if self.data:
            # Update from post
        #    data.update(self.data)
        #    data["dnssec_enabled"] = not self.data.get("dnssec_disabled", False)
        data = {
            "device": {
                "type": "omnia",
                "revision": "0",
            },
            "ports": {
                "unassigned": [
                    {"kind": "usb", "module_index": 0, "index": 0, "pos": "back", "name": "USB 0"},
                ],
                "wan": [
                    {"kind": "eth", "module_index": 0, "index": 0, "pos": "back", "name": "ETH 0"},
                ],
                "lan": [
                    {"kind": "eth", "module_index": 0, "index": 2, "pos": "back", "name": "ETH 2"},
                    {"kind": "eth", "module_index": 0, "index": 3, "pos": "back", "name": "ETH 3"},
                    {"kind": "eth", "module_index": 0, "index": 4, "pos": "back", "name": "ETH 4"},
                    {"kind": "eth", "module_index": 0, "index": 5, "pos": "back", "name": "ETH 5"},
                ],
                "guest": [
                    {"kind": "eth", "module_index": 0, "index": 1, "pos": "back", "name": "ETH 1"},
                ],
            }
        }
        for group in data["ports"].values():
            for port in group:
                port["id"] = "%s-%d-%d" % (port["kind"], port["module_index"], port["index"])

        self.backend_data = data

    def __init__(self, *args, **kwargs):
        self.load_backend_data()
        super(PortsHandler, self).__init__(*args, **kwargs)

    def get_form(self):
        ports_form = fapi.ForisForm("ports", self.data)
        ports_section = ports_form.add_section(name="set_ports", title=_(self.userfriendly_title))
        checkboxes = []
        for kind in ["wan", "lan", "guest", "unassigned"]:
            checkboxes += [(e["id"], e["id"]) for e in self.backend_data["ports"][kind]]
        ports_section.add_field(MultiCheckbox, name="wan", args=checkboxes, multifield=True)
        ports_section.add_field(MultiCheckbox, name="lan", args=checkboxes, multifield=True)
        ports_section.add_field(MultiCheckbox, name="guest", args=checkboxes, multifield=True)
        ports_section.add_field(MultiCheckbox, name="unassigned", args=checkboxes, multifield=True)

        def ports_form_cb(data):
            wan = data.get("wan", [])
            lan = data.get("lan", [])
            guest = data.get("guest", [])
            unassigned = data.get("unassigned", [])

            # TODO convert ids
            # result = current_state.backend.perform(
            #    "ports", "update_settings", {
            #        "lan": lan, "wan": wan, "guest": guest, "unassigned": unassigned
            #    }
            # )
            return "save_result", {"result": True}

        ports_form.add_callback(ports_form_cb)

        return ports_form
