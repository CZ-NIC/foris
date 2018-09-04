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

import copy

from .base import BaseConfigHandler

from foris import fapi

from foris.form import MultiCheckbox
from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, _


class NetworksHandler(BaseConfigHandler):
    """ Networks settings handler
    """
    userfriendly_title = gettext("Networks")

    def load_backend_data(self):
        data = current_state.backend.perform("networks", "get_settings")

        self.backend_data = data

    def __init__(self, *args, **kwargs):
        self.load_backend_data()
        super(NetworksHandler, self).__init__(*args, **kwargs)

    def get_form(self):
        data = copy.deepcopy(self.backend_data)

        if self.data:
            # Update from post
            data.update(self.data)

        networks_form = fapi.ForisForm("networks", self.data)
        ports_section = networks_form.add_section(
            name="set_ports", title=_(self.userfriendly_title))
        checkboxes = []
        for kind in ["wan", "lan", "guest", "none"]:
            checkboxes += [(e["id"], e["id"]) for e in self.backend_data["networks"][kind]]
        ports_section.add_field(MultiCheckbox, name="wan", args=checkboxes, multifield=True)
        ports_section.add_field(MultiCheckbox, name="lan", args=checkboxes, multifield=True)
        ports_section.add_field(MultiCheckbox, name="guest", args=checkboxes, multifield=True)
        ports_section.add_field(MultiCheckbox, name="none", args=checkboxes, multifield=True)

        def networks_form_cb(data):
            wan = data.get("wan", [])
            lan = data.get("lan", [])
            guest = data.get("guest", [])
            none = data.get("none", [])

            result = current_state.backend.perform(
                "networks", "update_settings", {
                    "networks": {"lan": lan, "wan": wan, "guest": guest, "none": none}
                }
            )
            return "save_result", result

        networks_form.add_callback(networks_form_cb)

        return networks_form
