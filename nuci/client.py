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

from ncclient import manager
from ncclient.operations import RPCError
from ncclient.operations.errors import TimeoutExpiredError
from xml.etree import cElementTree as ET
import logging

from modules import maintain, password as password_module, registration, uci_raw, time, updater
from modules.base import Data, YinElement
from nuci import filters
from nuci.exceptions import ConfigRestoreError
from nuci.modules import stats


logger = logging.getLogger("nuci.client")

BIN_PATH = "/usr/bin/nuci"


def set_bin_path(path):
    global BIN_PATH
    BIN_PATH = path


def get(filter=None):
    with manager.connect(BIN_PATH) as m:
        data = m.get(filter=("subtree", filter) if filter is not None else None).data_ele
        reply_data = Data()
        for elem in data.iter():
            if elem.tag == uci_raw.Uci.qual_tag("uci"):
                reply_data.add(uci_raw.Uci.from_element(elem))
            elif elem.tag == time.Time.qual_tag("time"):
                reply_data.add(time.Time.from_element(elem))
            elif elem.tag == updater.Updater.qual_tag("updater"):
                reply_data.add(updater.Updater.from_element(elem))
            elif elem.tag == stats.Stats.qual_tag("stats"):
                reply_data.add(stats.Stats.from_element(elem))
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
        import base64
        data = base64.b64encode(file.read())
        logger.debug(ET.tostring(maintain.Maintain.rpc_config_restore(data)))
        dispatch(maintain.Maintain.rpc_config_restore(data))
        return True
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
            import base64
            f.write(base64.b64decode(encoded_data))
        return True
    except (RPCError, TimeoutExpiredError):
        logger.exception("Config backup failed.")
        return False
    except TypeError:
        logger.exception("Can't decode backup file, this is probably a bug in Nuci backend.")
        return False


def get_registration():
    get_tag = registration.RegNum.qual_tag("get")
    element = ET.Element(get_tag)
    try:
        data = dispatch(element)
        return registration.RegNum.from_element(ET.fromstring(data.xml))
    except (RPCError, TimeoutExpiredError):
        return None


def ntp_update():
    get_tag = time.Time.qual_tag("ntp")
    element = ET.Element(get_tag)
    try:
        dispatch(element)
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
        dispatch(time.Time.rpc_set_iso8601(time_string))
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


def check_updates():
    check_tag = updater.Updater.qual_tag("check")
    element = ET.Element(check_tag)
    try:
        dispatch(element)
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def get_updater_status():
    data = get(filter=filters.updater)
    updater_status = data.find_child("updater")

    if updater_status.running:
        return "running", updater_status.running, updater_status.last_activity
    elif updater_status.failed:
        return "failed", updater_status.failed, updater_status.last_activity
    else:
        return "done", None, updater_status.last_activity


def get_uci_config():
    with manager.connect(BIN_PATH) as m:
        data = m.get_config("running").data_ele
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
    with manager.connect(BIN_PATH) as m:
        config_root = ET.Element(YinElement.qual_tag("config"))
        config_root.append(config)
        return m.edit_config("running", config=config_root)


def edit_config_multiple(configs):
    with manager.connect(BIN_PATH) as m:
        for config in configs:
            config_root = ET.Element(YinElement.qual_tag("config"))
            config_root.append(config)
            m.edit_config("running", config=config_root)


def dispatch(*args, **kwargs):
    with manager.connect(BIN_PATH) as m:
        return m.dispatch(*args, **kwargs)


if __name__ == '__main__':
    # development tests
    def _recursive_print(element, depth=0):
        if depth > 0:
            print "--" * depth,
        print element, element.path
        for child in element.children:
            _recursive_print(child, depth + 1)

    _recursive_print(get())
