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

    def __init__(self, env_key, timeout):
        self.cookie_set_needed = False
        self.cookie_unset_needed = False
        self.env_key = env_key
        self.timeout = timeout

    @property
    def session_id(self):
        return self._session.session_id

    @property
    def destroyed(self):
        return self._session.destroyed

    @property
    def is_anonymous(self):
        return self.session_id == UbusSession.ANONYMOUS

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

    def unload(self):
        self.unset_cookie()
        logger.debug("session '%s' cookies will be unloaded" % self.session_id)

    def load(self):
        self.set_cookie()
        logger.debug("session '%s' cookies will be loaded" % self.session_id)

    def destroy(self):
        self._session.destroy()
        self.tainted = False
        logger.debug("ws session '%s' destroyed" % self.session_id)


class SessionWsProxy(SessionProxy):
    def __init__(self, env_key, timeout, session_id=None):
        super(SessionWsProxy, self).__init__(env_key, timeout)
        self._session = UbusSession(self.timeout, session_id)

        if session_id is None:
            # grant listen for the new session
            self.grant_listen()
            # set the cookie
            self.set_cookie()

        logger.debug("ws session '%s' loaded" % self.session_id)

    def grant_listen(self):
        self._session.grant("websocket-listen", "listen-allowed")


class SessionForisProxy(SessionProxy):
    DONT_STORE_IN_ANONYMOUS = [
        "user_authenticated",
    ]

    def __init__(self, env_key, timeout, session_id):
        super(SessionForisProxy, self).__init__(env_key, timeout)
        self._session = UbusSession(self.timeout, session_id)
        self.tainted = False
        if self.is_anonymous:
            self._session.filtered_keys = list(SessionForisProxy.DONT_STORE_IN_ANONYMOUS)
        self.ws_session = None
        logger.debug("session '%s' loaded" % self.session_id)

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
        if self.ws_session:
            self.ws_session.destroy()

    def recreate(self):
        if not self.is_anonymous:
            self.unload()
            self.ws_session.unload()
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
        self._session.filtered_keys = list(SessionForisProxy.DONT_STORE_IN_ANONYMOUS)
        self.ws_session = None


class SessionMiddleware(object):

    @staticmethod
    def _get_cookie(name, cookies):
        filtered = [
            e.strip() for e in cookies.split(";") if e.strip().startswith("%s=" % name)
        ]
        return filtered[0][len(name) + 1:] if filtered else None

    def __init__(self, wrap_app, timeout, env_key="foris.session", ws_key="foris.ws.session"):
        self.timeout = timeout
        self.env_key = env_key
        self.ws_key = ws_key
        self.wrap_app = self.app = wrap_app

    def __call__(self, environ, start_response):
        cookies = environ.get('HTTP_COOKIE', "")
        session_key = self._get_cookie(self.env_key, cookies)
        session_key = session_key if session_key else UbusSession.ANONYMOUS
        ws_session_key = self._get_cookie(self.ws_key, cookies)

        try:
            session = SessionForisProxy(self.env_key, self.timeout, session_key)
        except SessionNotFound:
            session = SessionForisProxy(self.env_key, self.timeout, UbusSession.ANONYMOUS)

        if not session.is_anonymous:
            try:
                ws_session = SessionWsProxy(self.ws_key, self.timeout, ws_session_key)
            except SessionNotFound:
                ws_session = SessionWsProxy(self.ws_key, self.timeout)
        else:
            ws_session = None

        session.ws_session = ws_session

        environ["foris.session"] = session
        environ["foris.session.id"] = session.session_id
        environ["foris.session.data"] = session._session._data

        def session_start_response(status, headers, exc_info=None):
            response = start_response(status, headers, exc_info)
            # update ws session cookies
            if ws_session and ws_session.cookie_set_needed:
                headers.append(('Set-cookie', ws_session.set_cookie_text))
            elif ws_session and ws_session.cookie_unset_needed:
                headers.append(('Set-cookie', ws_session.unset_cookie_text))

            # update foris session cookies
            if session.cookie_set_needed:
                headers.append(('Set-cookie', session.set_cookie_text))
            elif session.cookie_unset_needed:
                headers.append(('Set-cookie', session.unset_cookie_text))

            # Store the current session if it was modified
            if session.tainted:
                session.save()

            return response

        return self.wrap_app(environ, session_start_response)
