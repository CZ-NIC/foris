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

import base64
import logging
import os
import shlex

from time import sleep, time
from xml.etree import cElementTree as ET

from ncclient import operations, transport
from ncclient.capabilities import Capabilities
from ncclient.manager import OpExecutor, CAPABILITIES
from ncclient.operations import RPCError
from ncclient.operations.errors import TimeoutExpiredError
from ncclient.transport import TransportError


from . import filters
from .exceptions import ConfigRestoreError
from .modules import (
    maintain, network, password as password_module, registration,
    stats, time as time_module, uci_raw, updater, user_notify
)
from .modules.base import Data, YinElement
from .utils import LocalizableTextValue
from foris.utils.translators import _

logger = logging.getLogger("nuci.client")


class StaticNetconfConnection(object):
    """
    Static connection to Netconf/Nuci, kept open during the whole run
    of Foris. Same API as ncclient's Manager class.
    """
    BIN_PATH = "/usr/bin/nuci"

    # recycle session if older than MAXIMUM_SESSION_LIFE seconds
    MAXIMUM_SESSION_LIFE = 300

    # maximum retries for reconnection if NETCONF server dies unexpectedly
    MAXIMUM_CONNECTION_RETRIES = 3

    # instance of singleton
    _inst = None

    # Manager properties
    _session = None
    _timeout = 30
    _async_mode = False
    _raise_mode = operations.RaiseMode.ALL

    # flag for lock during command execution
    _executing = False

    # when to restart the current persistent session
    session_kill_time = 0

    # remaining connection retries counter
    remaining_connection_retries = MAXIMUM_CONNECTION_RETRIES

    __metaclass__ = OpExecutor

    def __new__(cls, *args):
        """Initialize singleton instance or return an existing one.

        :return: instance of StaticNetconfConnection singleton
        """
        if cls._inst is None:
            cls._inst = super(StaticNetconfConnection, cls).__new__(cls, *args)
        return cls._inst

    @classmethod
    def reset_connection_retries(cls):
        cls.remaining_connection_retries = cls.MAXIMUM_CONNECTION_RETRIES

    @classmethod
    def _connect(cls):
        if cls._session is not None:
            cls._session.close()
        session = transport.StdIOSession(Capabilities(CAPABILITIES))
        session.connect(path=shlex.split(cls.BIN_PATH))
        cls._session = session

    @classmethod
    def execute(cls, klass, *args, **kwargs):
        while cls._executing:
            sleep(0.1)
        cls._executing = True
        try:
            if cls._session is None or time() > cls.session_kill_time:
                cls._connect()
                cls.session_kill_time = time() + cls.MAXIMUM_SESSION_LIFE
            timeout = kwargs.pop("timeout", cls._timeout)
            result = klass(cls._session,
                           async=cls._async_mode,
                           timeout=timeout,
                           raise_mode=cls._raise_mode).request(*args, **kwargs)
            # Everything OK, reset retries counter
            cls.reset_connection_retries()
        except (IOError, TransportError) as e:
            if cls.remaining_connection_retries <= 0:
                # Fail with an error...
                logger.critical("Unable to revive the NETCONF server.")
                # ... but make it possible to reconnect in the next call
                cls.reset_connection_retries()
                raise e
            logger.exception("Connection to NETCONF failed, retrying.")
            cls.remaining_connection_retries -= 1
            cls._session = None
            cls._executing = False
            return cls.execute(klass, *args, **kwargs)
        finally:
            cls._executing = False
        return result

    @classmethod
    def set_bin_path(cls, path):
        """
        Set path to Netconf binary (when using StdIO transport).

        :param path: path to Netconf binary
        :return: None
        """
        cls.BIN_PATH = path
        if cls._session:
            # reconnect to new binary
            cls._connect()

    @classmethod
    def enable_test_environment(cls, path):
        """
        Enable test environment - set environment variables read by Nuci.

        :param path: path to directory with test config files
        :return: None
        """
        os.environ["NUCI_TEST_CONFIG_DIR"] = path
        os.environ["NUCI_DONT_RESTART"] = "1"
        cls._connect()


# open persistent connection to Nuci
#netconf = StaticNetconfConnection()
netconf = None  # disable to connect


def get(filter=None):
    data = netconf.get(filter=("subtree", filter) if filter is not None else None).data_ele
    reply_data = Data()
    for elem in data.iter():
        if elem.tag == uci_raw.Uci.qual_tag("uci"):
            reply_data.add(uci_raw.Uci.from_element(elem))
        elif elem.tag == time_module.Time.qual_tag("time"):
            reply_data.add(time_module.Time.from_element(elem))
        elif elem.tag == updater.Updater.qual_tag("updater"):
            reply_data.add(updater.Updater.from_element(elem))
        elif elem.tag == stats.Stats.qual_tag("stats"):
            reply_data.add(stats.Stats.from_element(elem))
        elif elem.tag == user_notify.UserNotify.qual_tag("messages"):
            reply_data.add(user_notify.Messages.from_element(elem))
    return reply_data


def reboot():
    try:
        dispatch(maintain.Maintain.rpc_reboot())
        return True
    except (RPCError, TimeoutExpiredError):
        logger.exception("Reboot failed.")
        return False


def load_config_backup(file):
    try:
        data = base64.b64encode(file.read())
        logger.debug(ET.tostring(maintain.Maintain.rpc_config_restore(data)))
        data = dispatch(maintain.Maintain.rpc_config_restore(data))
        return maintain.Maintain.get_new_ip(ET.fromstring(data.xml))
    except RPCError:
        logger.exception("Unable to restore backup.")
        raise ConfigRestoreError("Unable to restore backup.")
    except TimeoutExpiredError:
        logger.exception("Timeout expired during backup restore.")
        raise


def save_config_backup(filename):
    try:
        data = dispatch(maintain.Maintain.rpc_config_backup())
        encoded_data = maintain.Maintain.from_element(ET.fromstring(data.xml)).data
        with open(filename, "wb") as f:
            # simple encoded_data.decode("base64") raises too general exceptions on failure
            f.write(base64.b64decode(encoded_data))
        return True
    except (RPCError, TimeoutExpiredError):
        logger.exception("Config backup failed.")
        return False
    except TypeError:
        logger.exception("Can't decode backup file, this is probably a bug in Nuci backend.")
        return False


def get_registration():
    try:
        data = dispatch(registration.RegNum.rpc_get())
        return registration.RegNum.from_element(ET.fromstring(data.xml))
    except (RPCError, TimeoutExpiredError):
        return None


def get_serial():
    try:
        data = dispatch(registration.Serial.rpc_serial())
        return registration.Serial.from_element(ET.fromstring(data.xml))
    except (RPCError, TimeoutExpiredError):
        return None


def get_registration_status(email, lang=None):
    try:
        data = dispatch(registration.RegistrationStatus.rpc_get_status(email, lang))
        return True, registration.RegistrationStatus.from_element(ET.fromstring(data.xml))
    except RPCError as e:
        return False, e.message
    except TimeoutExpiredError:
        return False, "Timed out."


def get_messages():
    try:
        return get(filter=filters.messages).find_child("messages") or user_notify.Messages()
    except (RPCError, TimeoutExpiredError):
        logger.exception("Unable to fetch messages")
        error_message = user_notify.Message(
            message_id=None,
            body=LocalizableTextValue(_("Unable to retrieve notifications, "
                                        "please try refreshing the page.")),
            severity="error",
            timestamp=int(time())
        )
        return user_notify.Messages(messages=[error_message])


def dismiss_notifications(message_ids):
    try:
        logger.debug(message_ids)
        logger.debug(ET.tostring(user_notify.UserNotify.rpc_display(message_ids)))
        dispatch(user_notify.UserNotify.rpc_display(message_ids))
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def test_notifications():
    try:
        dispatch(user_notify.UserNotify.rpc_test())
        return True, None
    except RPCError as e:
        if e.tag == "operation-failed":
            return False, e.message
        logger.exception("Notifications testing failed.")
    except TimeoutExpiredError:
        logger.exception("Notifications testing timed out.")
    return False, None


def ntp_update():
    get_tag = time_module.Time.qual_tag("ntp")
    element = ET.Element(get_tag)
    try:
        # Use longer timeout, because the NTP sync takes some time...
        dispatch(element, timeout=60)
        return True
    except (RPCError, TimeoutExpiredError):
        # TODO: maybe be more precise and determine what happened
        return False


def set_time(time_string):
    """Set time on device.

    :param time_string: time to set in ISO 8601 format
    :return:
    """
    try:
        dispatch(time_module.Time.rpc_set_iso8601(time_string))
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def set_password(user, password):
    """Set password of system user.

    :param user: user for which to set the password
    :param password: password to set
    :return: True on success, False otherwise
    """
    try:
        dispatch(password_module.Password(user, password).rpc_set)
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def deny_approval(approval_id):
    """Deny updater approval

    :param approval_id: an id of an approval
    :return: True on success, False otherwise
    """
    try:
        dispatch(updater.Updater.rpc_deny(approval_id))
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def approve_approval(approval_id):
    """Approve updater approval

    :param approval_id: an id of an approval
    :return: True on success, False otherwise
    """
    try:
        dispatch(updater.Updater.rpc_grant(approval_id))
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def update_contract_status():
    """Triggers a script which updates contract validity status in uci

    :return: True on success, False otherwise
    """
    try:
        dispatch(registration.ContractUpdate().rcp_update_contract)
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def check_connection():
    """Check for connectivity features returned by network check RPC.

    :return: Connection instance on success, None otherwise
    """
    try:
        data = dispatch(network.Connection.rpc_check())
        return network.Connection.from_element(ET.fromstring(data.xml))
    except (RPCError, TimeoutExpiredError):
        return None


def check_updates():
    check_tag = updater.Updater.qual_tag("check")
    element = ET.Element(check_tag)
    try:
        dispatch(element)
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def get_updater_status():
    """Get current status of last/current run of updater.

    :return: tuple of three: (status, status_message, list of last_activity)
    """
    data = get(filter=filters.updater)
    updater_status = data.find_child("updater")

    if updater_status.running:
        return "running", updater_status.running, updater_status.last_activity
    elif updater_status.failed is not False:
        return "failed", updater_status.failed, updater_status.last_activity
    elif updater_status.offline_pending:
        return "offline_pending", None, updater_status.last_activity
    else:
        return "done", None, updater_status.last_activity


def get_uci_config():
    data = netconf.get_config("running").data_ele
    reply_data = Data()
    reply_data.add(uci_raw.Uci.from_element(data.find(uci_raw.Uci.qual_tag("uci"))))
    return reply_data


def edit_uci_config(uci):
    """Create proper Uci config for given Uci element and save it.

    :param uci: config to write
    :return:
    """
    if not isinstance(uci, uci_raw.Uci):
        raise ValueError("Unknown type: %s" % type(uci))
    edit_config(uci.get_tree())


def edit_config(config):
    """Execute netconf edit-config.

    :param config: config to edit as an XML Element
    :return:
    """
    config_root = ET.Element(YinElement.qual_tag("config"))
    config_root.append(config)
    return netconf.edit_config("running", config=config_root)


def edit_config_multiple(configs):
    for config in configs:
        config_root = ET.Element(YinElement.qual_tag("config"))
        config_root.append(config)
        netconf.edit_config("running", config=config_root)


def dispatch(*args, **kwargs):
    return netconf.dispatch(*args, **kwargs)
