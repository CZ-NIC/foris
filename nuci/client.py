from ncclient import manager
from ncclient.operations import RPCError
from xml.etree import cElementTree as ET
import logging

from modules import registration, uci_raw, time, updater
from modules.base import Data, YinElement


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
        return reply_data


def get_registration():
    get_tag = registration.RegNum.qual_tag("get")
    element = ET.Element(get_tag)
    data = dispatch(element)
    return registration.RegNum.from_element(ET.fromstring(data.xml))


def ntp_update():
    get_tag = time.Time.qual_tag("ntp")
    element = ET.Element(get_tag)
    try:
        dispatch(element)
        return True
    except RPCError:
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
    except RPCError:
        return False



def check_updates():
    check_tag = updater.Updater.qual_tag("check")
    element = ET.Element(check_tag)
    try:
        dispatch(element)
        return True
    except RPCError:
        return False


def get_updater_status():
    data = get(filter=ET.Element(updater.Updater.qual_tag("updater")))
    updater_status = data.find_child("updater")

    if updater_status.running:
        return "running", updater_status.running
    elif updater_status.failed:
        return "failed", updater_status.failed
    else:
        return "done", None


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