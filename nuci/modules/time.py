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

####################################################################################################
ET.register_namespace("time", Time.NS_URI)