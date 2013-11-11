"""
This module contains filters used for subtree filtering in nuci client. Filter is basically
an XML element that is passed to client.get() function and appropriate subtree is returned.
"""

from nuci.modules import time, uci_raw, updater
import xml.etree.cElementTree as ET


# top-level containers
uci = ET.Element(uci_raw.Uci.qual_tag("uci"))
updater = ET.Element(updater.Updater.qual_tag("updater"))
time = ET.Element(time.Time.qual_tag("time"))


# factory for uci configs
def create_uci_config(config_name):
    _uci = uci_raw.Uci()
    _config = uci_raw.Config(config_name)
    _uci.add(_config)
    return _config.get_tree()


foris_config = create_uci_config("foris")
