# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2017 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

from foris import fapi
from foris.form import File
from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, _

from .base import BaseConfigHandler


class MaintenanceHandler(BaseConfigHandler):
    userfriendly_title = gettext("Maintenance")

    def get_form(self):
        maintenance_form = fapi.ForisForm("maintenance", self.data)
        maintenance_main = maintenance_form.add_section(
            name="restore_backup", title=_(self.userfriendly_title)
        )
        maintenance_main.add_field(File, name="backup_file", label=_("Backup file"), required=True)

        def maintenance_form_cb(data):
            data = current_state.backend.perform(
                "maintain",
                "restore_backup",
                {"backup": base64.b64encode(data["backup_file"].file.read()).decode("utf-8")},
            )
            return "save_result", {"result": data["result"]}

        maintenance_form.add_callback(maintenance_form_cb)
        return maintenance_form
