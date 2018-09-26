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

from foris.form import Hidden
from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, _


class ProfileHandler(BaseConfigHandler):
    """ Profile settings handler
    """
    userfriendly_title = gettext("Guide workflow")

    def __init__(self, *args, **kwargs):
        self.load_backend_data()
        super(ProfileHandler, self).__init__(*args, **kwargs)

    def load_backend_data(self):
        self.backend_data = current_state.backend.perform("web", "get_guide")

    def get_form(self):

        data = {"workflow": self.backend_data["current_workflow"]}
        if self.data:
            data.update(self.data)

        profile_form = fapi.ForisForm("profile", data)
        main = profile_form.add_section(name="set_profile", title=_(self.userfriendly_title))
        main.add_field(Hidden, name="workflow", value=self.backend_data["current_workflow"])

        def profile_form_cb(data):
            result = current_state.backend.perform(
                "web", "update_guide", {
                    "enabled": True,
                    "workflow": data["workflow"],
                }
            )
            return "save_result", result

        profile_form.add_callback(profile_form_cb)

        return profile_form
