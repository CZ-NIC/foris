"""
This module contains filters used for subtree filtering in nuci client. Filter is basically
an XML element that is passed to client.get() function and appropriate subtree is returned.
"""

from nuci.modules import time, uci_raw, updater
import xml.etree.cElementTree as ET


uci = ET.Element(uci_raw.Uci.qual_tag("uci"))
updater = ET.Element(updater.Updater.qual_tag("updater"))
time = ET.Element(time.Time.qual_tag("time"))