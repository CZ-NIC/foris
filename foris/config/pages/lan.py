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

from datetime import datetime

from foris.config_handlers import lan

from .base import ConfigPageMixin


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
            if client["expires"] > 0:
                client["expires"] = datetime.utcfromtimestamp(client["expires"]).strftime(
                    "%Y-%m-%d %H:%M"
                )
            else:
                client["expires"] = "N/A"

        return super(LanConfigPage, self).render(**kwargs)
