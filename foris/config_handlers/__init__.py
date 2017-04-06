# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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
    CollectionToggleHandler,
    DNSHandler,
    LanHandler,
    MaintenanceHandler,
    NotificationsHandler,
    PasswordHandler,
    RegionHandler,
    RegistrationCheckHandler,
    SystemPasswordHandler,
    TimeHandler,
    UcollectHandler,
    UpdaterEulaHandler,
    UpdaterHandler,
    WanHandler,
)

from .wifi import WifiHandler

__all__ = [
    'BaseConfigHandler',
    'CollectionToggleHandler',
    'DNSHandler',
    'LanHandler',
    'MaintenanceHandler',
    'NotificationsHandler',
    'PasswordHandler',
    'RegionHandler',
    'RegistrationCheckHandler',
    'SystemPasswordHandler',
    'TimeHandler',
    'UcollectHandler',
    'UpdaterEulaHandler',
    'UpdaterHandler',
    'WanHandler',
    'WifiHandler',
]
