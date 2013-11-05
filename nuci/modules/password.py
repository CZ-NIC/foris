from base import YinElement
from xml.etree import cElementTree as ET


class Password(YinElement):
    NS_URI = "http://www.nic.cz/ns/router/password"

    def __init__(self, user, password):
        super(Password, self).__init__()
        self.user = user
        self.password = password

    @property
    def rpc_set(self):
        set_tag = Password.qual_tag("set")
        element = ET.Element(set_tag)
        user_elem = ET.SubElement(element, Password.qual_tag("user"))
        user_elem.text = self.user
        password_elem = ET.SubElement(element, Password.qual_tag("password"))
        password_elem.text = self.password
        return element

####################################################################################################
ET.register_namespace("password", Password.NS_URI)