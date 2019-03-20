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

from foris.guide import Workflow

from foris.config_handlers import profile, misc
from foris.state import current_state
from foris.utils import messages
from foris.utils.translators import _

from .base import ConfigPageMixin


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
