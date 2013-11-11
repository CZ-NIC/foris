from base import YinElement
from xml.etree import cElementTree as ET


class Uci(YinElement):
    tag = "uci"
    NS_URI = "http://www.nic.cz/ns/router/uci-raw"

    @staticmethod
    def from_element(element):
        uci = Uci()
        config_elems = element.findall(Uci.qual_tag("config"))
        for config_elem in config_elems:
            config = Config.from_element(config_elem)
            uci.add(config)
        else:
            pass  # just return an empty UciElement
        return uci

    @property
    def key(self):
        return "uci"

    def __str__(self):
        return "Uci configuration"


class Config(Uci):
    tag = "config"

    def __init__(self, name):
        super(Config, self).__init__()
        self.name = name

    def __str__(self):
        return "Config " + self.name

    def _append_subelements(self, element):
        ET.SubElement(element, self.qual_tag("name")).text = self.name

    @property
    def key(self):
        return self.name

    @staticmethod
    def from_element(element):
        name = element.find(Config.qual_tag("name")).text
        config = Config(name)
        section_elems = element.findall(Config.qual_tag("section"))
        for section_elem in section_elems:
            section = Section.from_element(section_elem)
            config.add(section)
        else:
            pass  # just return an empty ConfigElement
        return config


class Section(Uci):
    tag = "section"

    def __init__(self, name, type, anonymous=False):
        super(Section, self).__init__()
        self.name = name
        self.type = type
        self.anonymous = anonymous

    def __str__(self):
        return "Section %s %s%s" % (self.name, self.type,
                                    " (anonymous)" if self.anonymous else "")

    @property
    def key(self):
        return self.name

    @staticmethod
    def from_element(element):
        name = element.find(Section.qual_tag("name")).text
        type_ = element.find(Section.qual_tag("type")).text
        anonymous = element.find(Section.qual_tag("anonymous")) is not None
        section = Section(name, type_, anonymous)
        for elem in element.iter():
            if elem.tag == Option.qual_tag("option"):
                section.add(Option.from_element(elem))
            elif elem.tag == List.qual_tag("list"):
                section.add(List.from_element(elem))
        return section

    def _append_subelements(self, element):
        ET.SubElement(element, self.qual_tag("name")).text = self.name
        ET.SubElement(element, self.qual_tag("type")).text = self.type
        if self.anonymous:
            ET.SubElement(element, self.qual_tag("anonymous"))


class Option(Uci):
    tag = "option"
    final = True

    def __init__(self, name, value):
        super(Option, self).__init__()
        self.name = name
        if isinstance(value, bool):
            value = "1" if value else "0"
        self.value = str(value)

    def __str__(self):
        return "Option %s: %s" % (self.name, self.value)

    @property
    def key(self):
        return self.name

    @staticmethod
    def from_element(element):
        name = element.find(Option.qual_tag("name")).text
        value = element.find(Option.qual_tag("value")).text
        option = Option(name, value)
        return option

    def _append_subelements(self, element):
        ET.SubElement(element, self.qual_tag("name")).text = self.name
        ET.SubElement(element, self.qual_tag("value")).text = self.value


class List(Uci):
    tag = "list"

    def __init__(self, name):
        super(List, self).__init__()
        self.name = name

    def __str__(self):
        return "List " + self.name

    @property
    def key(self):
        return self.name

    @staticmethod
    def from_element(element):
        name = element.find(List.qual_tag("name")).text
        list_ = List(name)
        for value_elem in element.findall(List.qual_tag("value")):
            value = Value.from_element(value_elem)
            list_.add(value)
        return list_

    def _append_subelements(self, element):
        ET.SubElement(element, self.qual_tag("name")).text = self.name

    def get_tree(self, subelement=None):
        element = self.to_element()
        if subelement is not None:
            element.append(subelement)
        if self.operation == "create":
            # list can't be empty - append all the children
            for child in self.children:
                element.append(child.to_element())

        if self.parent:
            return self.parent.get_tree(element)
        else:
            return element


class Value(Uci):
    tag = "value"
    final = True

    def __init__(self, index, content):
        super(Value, self).__init__()
        self.index = str(index)
        self.content = str(content)

    def __str__(self):
        return "Value #%s: %s" % (self.index, self.content)

    @property
    def key(self):
        return self.index

    @staticmethod
    def from_element(element):
        index = element.find(Value.qual_tag("index")).text
        content = element.find(Value.qual_tag("content")).text
        value = Value(index, content)
        return value

    def _append_subelements(self, element):
        ET.SubElement(element, self.qual_tag("index")).text = self.index
        ET.SubElement(element, self.qual_tag("content")).text = self.content


####################################################################################################
ET.register_namespace("uci", Uci.NS_URI)