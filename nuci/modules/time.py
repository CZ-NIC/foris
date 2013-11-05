from base import YinElement
from xml.etree import cElementTree as ET


class Time(YinElement):
    tag = "time"
    NS_URI = "http://www.nic.cz/ns/router/time"

    def __init__(self, local, timezone, utc):
        super(Time, self).__init__()
        self.local = local
        self.timezone = timezone
        self.utc = utc

    @staticmethod
    def from_element(element):
        local = element.find(Time.qual_tag("local")).text
        timezone = element.find(Time.qual_tag("timezone")).text
        utc = element.find(Time.qual_tag("utc")).text
        return Time(local, timezone, utc)

    @property
    def key(self):
        return "time"

    @staticmethod
    def rpc_set_iso8601(iso_time):
        set_tag = Time.qual_tag("set")
        element = ET.Element(set_tag)
        time_tag = Time.qual_tag("time")
        time_elem = ET.SubElement(element, time_tag)
        time_elem.text = iso_time
        # handling ISO dates with Python stdlib is pain...
        is_utc = iso_time.endswith("Z") or iso_time.endswith("UTC") or iso_time.endswith("+00") \
            or iso_time.endswith("+00:00") or iso_time.endswith("+0000")
        if is_utc:
            utc_tag = Time.qual_tag("utc")
            ET.SubElement(element, utc_tag)
        return element

####################################################################################################
ET.register_namespace("time", Time.NS_URI)