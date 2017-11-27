# Foris
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

import logging

logger = logging.getLogger("foris.backend")
from foris_client.buses.base import ControllerError


class ExceptionInBackend(Exception):
    def __init__(self, query, remote_stacktrace, remote_description):
        self.query = query
        self.remote_stacktrace = remote_stacktrace
        self.remote_description = remote_description


class Backend(object):
    DEFAULT_TIMEOUT = 30000  # in ms

    def __init__(self, name, path):
        self.name = name
        self.path = path

        if name == "ubus":
            from foris_client.buses.ubus import UbusSender
            self._instance = UbusSender(path, default_timeout=self.DEFAULT_TIMEOUT)

        elif name == "unix-socket":
            from foris.backend.buses.unix_socket import UnixSocketSender
            self._instance = UnixSocketSender(
                path, default_timeout=self.DEFAULT_TIMEOUT)

    def __repr__(self):
        return "%s('%s')" % (type(self._instance).__name__, self.path)

    def perform(self, module, action, data=None, raise_exception_on_failure=True):
        try:
            response = self._instance.send(module, action, data or {})
        except ControllerError as e:
            logger.error("Exception in backend occured.")
            if raise_exception_on_failure:
                error = e.errors[0]  # right now we are dealing only with the first error
                raise ExceptionInBackend(
                    {"module": module, "action": action, "kind": "request", "data": data or {}},
                    error["stacktrace"], error["description"]
                )

        return response
