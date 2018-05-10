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

from .base import (
    BaseConfigHandler,
)

from .backups import MaintenanceHandler
from .dns import DNSHandler
from .lan import LanHandler
from .misc import PasswordHandler, SystemPasswordHandler
from .notifications import NotificationsHandler
from .collect import CollectionToggleHandler, UcollectHandler, RegistrationCheckHandler
from .updater import UpdaterHandler
from .wan import WanHandler
from .wifi import WifiHandler

__all__ = [
    'BaseConfigHandler',
    'CollectionToggleHandler',
    'DNSHandler',
    'LanHandler',
    'MaintenanceHandler',
    'NotificationsHandler',
    'PasswordHandler',
    'RegistrationCheckHandler',
    'SystemPasswordHandler',
    'UcollectHandler',
    'UpdaterHandler',
    'WanHandler',
    'WifiHandler',
]
