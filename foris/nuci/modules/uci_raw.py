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

        # Note the type could be empty (when we filter the option - foris.settings.lang)
        #  <nc:data xmlns:nc="urn:ietf:params:xml:ns:netconf:base:1.0" xmlns:uci="http://www.nic.cz/ns/router/uci-raw">
        #    <uci:uci>
        #      <uci:config>
        #        <uci:name>foris</uci:name>
        #        <uci:section>
        #          <uci:name>settings</uci:name>
        #          <uci:option>
        #            <uci:name>lang</uci:name>
        #            <uci:value>en</uci:value>
        #          </uci:option>
        #        </uci:section>
        #      </uci:config>
        #    </uci:uci>
        #  </nc:data>

        type_node = element.find(Section.qual_tag("type"))
        type_ = type_node.text if type_node is not None else None

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
        if self.type is not None:
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
        elif isinstance(value, str):
            value = value.decode("utf8")
        self.value = unicode(value)

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
        if isinstance(content, str):
            content = content.decode("utf8")
        self.content = unicode(content)

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


def parse_uci_bool(value):
    """
    Helper function to parse Uci bool values.

    :param value: value - can be either Option instance or raw value
    :return: True or False
    """
    if isinstance(value, Option):
        value = value.value
    return value in ("1", "true", "yes", "on", True)


def build_option_uci_tree(uci_path, section_type, value):
    """
    Build a tree of Uci objects representing the hierarchy for a single
    Uci Option.

    :param uci_path: path to the Uci option
    :param section_type: type of the section (second part of the path)
    :param value: value for the option
    :return: Uci element containing the tree
    """
    chunks = uci_path.split(".")
    if len(chunks) != 3:
        raise ValueError("uci_path must have three elements")
    if "@" in chunks[1]:
        raise ValueError("Anonymous sections are not supported.")
    uci = Uci()
    config = Config(chunks[0])
    uci.add(config)
    section = Section(chunks[1], section_type)
    config.add(section)
    section.add(Option(chunks[2], value))

    return uci

####################################################################################################
ET.register_namespace("uci", Uci.NS_URI)
