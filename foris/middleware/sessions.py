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

import logging

from datetime import datetime

from foris.ubus.sessions import UbusSession, SessionNotFound

logger = logging.getLogger("middleware.sessions")


class SessionProxy(object):
    DONT_STORE_IN_ANONYMOUS = [
        "user_authenticated",
        "allowed_step_max",
        "wizard_finished",
    ]

    def __init__(self, env_key, timeout, session_id):
        self.cookie_set_needed = False
        self.cookie_unset_needed = False
        self.env_key = env_key
        self.timeout = timeout
        self._session = UbusSession(self.timeout, session_id)
        self.tainted = False
        if self.is_anonymous:
            self._session.filtered_keys = list(SessionProxy.DONT_STORE_IN_ANONYMOUS)
        logger.debug("session '%s' loaded" % self.session_id)

    def set_cookie(self):
        self.cookie_set_needed = True
        self._cookie_set_text = "; ".join([
            "%s=%s" % (self.env_key, self.session_id),
            "httponly",
            "Path=/",
        ]).encode("ascii")

    def unset_cookie(self):
        self.cookie_unset_needed = True
        self._cookie_unset_text = "; ".join([
            "%s=%s" % (self.env_key, self.session_id),
            "expires=%s" % datetime.strftime(datetime.utcnow(), "%a, %d %b %Y %T %zGMT"),
            "httponly",
            "Path=/",
        ]).encode("ascii")

    @property
    def set_cookie_text(self):
        return self._cookie_set_text

    @property
    def unset_cookie_text(self):
        return self._cookie_unset_text

    @property
    def session_id(self):
        return self._session.session_id

    @property
    def destroyed(self):
        return self._session.destroyed

    @property
    def is_anonymous(self):
        return self.session_id == UbusSession.ANONYMOUS

    def __len__(self):
        return self._session.__len__()

    def __setitem__(self, key, value):
        self.tainted = True
        return self._session.__setitem__(key, value)

    def __contains__(self, key):
        return self._session.__contains__(key)

    def __iter__(self):
        return self._session.__iter__()

    def __delitem__(self, key):
        self.tainted = True
        return self._session.__delitem__(key)

    def __getitem__(self, key):
        return self._session.__getitem__(key)

    def get(self, *args, **kwargs):
        return self._session.get(*args, **kwargs)

    def save(self):
        self._session.save()
        self.tainted = False
        logger.debug("session '%s' stored" % self.session_id)

    def destroy(self):
        self._session.destroy()
        self.tainted = False
        logger.debug("session '%s' destroyed" % self.session_id)

    def unload(self):
        self.unset_cookie()
        logger.debug("session '%s' unloaded" % self.session_id)

    def load(self):
        self.set_cookie()
        logger.debug("session '%s' loaded" % self.session_id)

    def recreate(self):
        if not self.is_anonymous:
            self.unload()
            self.destroy()

        self._session = UbusSession(self.timeout)
        logger.debug("session '%s' created" % self.session_id)
        self._session.filtered_keys = []
        self.load()

    def load_anonymous(self):
        if self.is_anonymous:
            return  # already loaded

        self.destroy()
        self.unload()
        self._session = UbusSession(self.timeout, session_id=UbusSession.ANONYMOUS)
        self._session.filtered_keys = list(SessionProxy.DONT_STORE_IN_ANONYMOUS)


class SessionMiddleware(object):

    def __init__(self, wrap_app, timeout, env_key="foris.session"):
        self.timeout = timeout
        self.env_key = env_key
        self.wrap_app = self.app = wrap_app

    def __call__(self, environ, start_response):
        cookies = environ.get('HTTP_COOKIE', "")
        cookie_data = [
            e.strip() for e in cookies.split(";") if e.strip().startswith("%s=" % self.env_key)
        ]

        if cookie_data:
            session_key = cookie_data[0][len(self.env_key) + 1:]
        else:
            session_key = UbusSession.ANONYMOUS

        try:
            session = SessionProxy(self.env_key, self.timeout, session_key)
        except SessionNotFound:
            session = SessionProxy(self.env_key, self.timeout, UbusSession.ANONYMOUS)

        environ["foris.session"] = session

        def session_start_response(status, headers, exc_info=None):
            response = start_response(status, headers, exc_info)
            if session.cookie_set_needed:
                headers.append(('Set-cookie', session.set_cookie_text))
            elif session.cookie_unset_needed:
                headers.append(('Set-cookie', session.unset_cookie_text))

            # Store the current session if it was modified
            if session.tainted:
                session.save()

            return response

        return self.wrap_app(environ, session_start_response)
