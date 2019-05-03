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


from foris.config_handlers import networks
from foris.state import current_state
from foris.utils import messages
from foris.utils.translators import _

from .base import ConfigPageMixin


class NetworksConfigPage(ConfigPageMixin, networks.NetworksHandler):
    slug = "networks"
    menu_order = 14
    template = "config/networks"
    template_type = "jinja2"

    def render(self, **kwargs):
        # place non-configurable intefaces in front of configurable
        kwargs["networks"] = {}
        for network_name in self.backend_data["networks"].keys():
            kwargs["networks"][network_name] = sorted(
                self.backend_data["networks"][network_name],
                key=lambda x: (1 if x["configurable"] else 0, x["slot"]),
                reverse=False,
            )
            for network in kwargs["networks"][network_name]:
                if network["type"] == "wifi":
                    network["slot"] = network["bus"] + network["slot"]

        # don't display inconfigurable devices in none network (can't be configured anyway)
        kwargs["networks"]["none"] = [e for e in kwargs["networks"]["none"] if e["configurable"]]

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
