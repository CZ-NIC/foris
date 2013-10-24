from base import YinElement
from xml.etree import cElementTree as ET


class RegNum(YinElement):
    tag = "reg-num"
    NS_URI = "http://www.nic.cz/ns/router/registration"

    def __init__(self, value):
        super(RegNum, self).__init__()
        self.value = value

    @staticmethod
    def from_element(element):
        value = element.find(RegNum.qual_tag(RegNum.tag)).text
        return RegNum(value)

    @property
    def key(self):
        return "reg-num"


####################################################################################################
ET.register_namespace("registration", RegNum.NS_URI)