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

import logging
import time

from foris_client.buses.base import ControllerError

logger = logging.getLogger("foris.backend")


class ExceptionInBackend(Exception):
    def __init__(self, query, remote_stacktrace, remote_description):
        self.query = query
        self.remote_stacktrace = remote_stacktrace
        self.remote_description = remote_description


class Backend(object):
    DEFAULT_TIMEOUT = 30000  # in ms

    def __init__(self, name, **kwargs):
        self.name = name
        self.controller_id = None

        if name == "ubus":
            from foris_client.buses.ubus import UbusSender

            self.path = kwargs["path"]
            self._instance = UbusSender(kwargs["path"], default_timeout=self.DEFAULT_TIMEOUT)

        elif name == "unix-socket":
            from foris_client.buses.unix_socket import UnixSocketSender

            self.path = kwargs["path"]
            self._instance = UnixSocketSender(kwargs["path"], default_timeout=self.DEFAULT_TIMEOUT)

        elif name == "mqtt":
            from foris_client.buses.mqtt import MqttSender

            self.host = kwargs["host"]
            self.port = kwargs["port"]
            self.credentials = kwargs["credentials"]
            self.controller_id = kwargs["controller_id"]
            self._instance = MqttSender(
                kwargs["host"],
                kwargs["port"],
                default_timeout=self.DEFAULT_TIMEOUT,
                credentials=kwargs["credentials"],
            )

    def __repr__(self):
        if self.name in ["unix-socket", "ubus"]:
            return "%s('%s')" % (type(self._instance).__name__, self.path)
        elif self.name == "mqtt":
            return "%s('%s:%d')" % (type(self._instance).__name__, self.host, self.port)
        return "%s" % type(self._instance).__name__

    def perform(
        self, module, action, data=None, raise_exception_on_failure=True, controller_id=None
    ):
        """ Perform backend action

        :returns: None on error, response data otherwise
        :rtype: NoneType or dict
        :raises ExceptionInBackend: When command failed and raise_exception_on_failure is True
        """
        response = None
        start_time = time.time()
        try:
            response = self._instance.send(
                module, action, data, controller_id=controller_id or self.controller_id
            )
        except ControllerError as e:
            logger.error("Exception in backend occured.")
            if raise_exception_on_failure:
                error = e.errors[0]  # right now we are dealing only with the first error
                msg = {"module": module, "action": action, "kind": "request"}
                if data is not None:
                    msg["data"] = data
                raise ExceptionInBackend(msg, error["stacktrace"], error["description"])
        except RuntimeError as e:
            # This may occure when e.g. calling function is not present in backend
            logger.error("RuntimeError occured during the communication with backend.")
            if raise_exception_on_failure:
                raise e
        except Exception as e:
            logger.error("Exception occured during the communication with backend. (%s)", e)
            raise e
        finally:
            logger.debug(
                "Query took %f: %s.%s - %s", time.time() - start_time, module, action, data
            )

        return response
