import logging

from . import call
from json import JSONEncoder

logger = logging.getLogger("ubus.sessions")


class SessionNotFound(Exception):
    pass


class SessionFailedToCreate(Exception):
    pass


class SessionDestroyed(Exception):
    pass


class SessionReadOnly(Exception):
    pass


def not_destroyed(func):
    def wrapped(self, *args, **kwargs):
        if self.destroyed:
            raise SessionDestroyed()
        return func(self, *args, **kwargs)
    return wrapped


def not_readonly(func):
    def wrapped(self, *args, **kwargs):
        if self.readonly:
            raise SessionReadOnly()
        return func(self, *args, **kwargs)
    return wrapped


class UbusSession(object):
    ANONYMOUS = '00000000000000000000000000000000'

    def _load_data(self, data):
        self.session_id = data["ubus_rpc_session"]
        self._data = data['data'].get("foris", {})
        self.expires_in = data["expires"]

    def _create(self, timeout):
        try:
            res = call("session", "create", {"timeout": timeout})
            self._load_data(res[0])
            logger.debug("Session '%s' created: %s" % (self.session_id, repr(res)))
        except RuntimeError:
            logger.debug("Failed to create a session.")
            raise SessionFailedToCreate()

    def _obtain(self, session_id):
        try:
            # This will renew session -> expires will be delayed
            res = call("session", "list", {"ubus_rpc_session": session_id})
            logger.debug("session '%s' obtained: %s" % (session_id, repr(res)))
            self._load_data(res[0])
        except RuntimeError:
            logger.debug("session '%s' not found." % session_id)
            raise SessionNotFound()

    def __init__(self, timeout, session_id=None):
        if not session_id:
            self._create(timeout)
        else:
            self._obtain(session_id)
        self.destroyed = False
        self.readonly = False

    @not_readonly
    @not_destroyed
    def save(self):
        try:
            call("session", "set", {
                "ubus_rpc_session": self.session_id, "values": {"foris": self._data}}
            )
            logger.debug("foris session '%s' stored: %s" % (self.session_id, self._data))
        except RuntimeError:
            logger.debug("Failed to store session data.")
            return False

        return True

    @not_readonly
    @not_destroyed
    def destroy(self):
        try:
            call("session", "destroy", {"ubus_rpc_session": self.session_id})
            logger.debug("foris session destroyed: %s" % self._data)
            self.destroyed = True
        except RuntimeError:
            logger.debug("Failed to store session data.")

    # make session iterable
    @not_destroyed
    def __getitem__(self, key):
        return self._data.get(key, None)

    @not_readonly
    @not_destroyed
    def __delitem__(self, key):
        self._data.pop(key, None)

    @not_destroyed
    def __iter__(self):
        for key in self._data:
            yield key

    @not_destroyed
    def __contains__(self, key):
        return key in self._data

    @not_readonly
    @not_destroyed
    def __setitem__(self, key, value):
        if not isinstance(key, str):
            raise TypeError("key is not a string")
        # test whether the key is ascii (exception will be raised otherwise)
        key.decode("ascii")
        # test whenter the value is json-serializable (exception otherwise)
        JSONEncoder().encode(value)
        self._data[key] = value

    @not_destroyed
    def __len__(self):
        return len(self._data)

    @not_destroyed
    def get(self, *args, **kwargs):
        return self._data.get(*args, **kwargs)
