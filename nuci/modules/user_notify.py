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
from datetime import datetime
from xml.etree import cElementTree as ET

from bottle import html_escape, cached_property

from base import YinElement
from nuci.utils import LocalizableTextValue


class UserNotify(YinElement):
    NS_URI = "http://www.nic.cz/ns/router/user-notify"

    def __init__(self):
        super(UserNotify, self).__init__()

    @staticmethod
    def rpc_test():
        test_tag = UserNotify.qual_tag("test")
        element = ET.Element(test_tag)
        return element

    @staticmethod
    def rpc_message(body, severity):
        message_tag = UserNotify.qual_tag("message")
        element = ET.Element(message_tag)
        body_elem = ET.SubElement(element, body)
        body_elem.text = body
        severity_elem = ET.SubElement(element, severity)
        severity_elem.text = severity
        return element

    @staticmethod
    def rpc_display(message_ids):
        display_tag = UserNotify.qual_tag("display")
        element = ET.Element(display_tag)
        if not hasattr(message_ids, '__iter__'):
            # if it's not a sequence, wrap in in a list
            message_ids = [message_ids]
        message_id_tag = UserNotify.qual_tag("message-id")
        for m_id in message_ids:
            m_id_elem = ET.SubElement(element, message_id_tag)
            m_id_elem.text = m_id
        return element


class Severity(object):
    NEWS = (10, "news")
    UPDATE = (20, "update")
    ERROR = (30, "error")
    RESTART = (40, "restart")

    ALLOWED_VALUES = (
        NEWS,
        UPDATE,
        ERROR,
        RESTART,
    )

    def __init__(self, severity, severity_string=None):
        if isinstance(severity, int):
            if severity_string:
                self.value = (severity, severity_string)
            else:
                self.value = (severity, self.get_string(severity))
        else:
            self.value = self.get_value(severity)

    def get_value(self, severity_string):
        for value in self.ALLOWED_VALUES:
            if value[1] == severity_string:
                return value
        raise ValueError("Unknown value for severity: '%s'" % severity_string)

    def get_string(self, severity_priority):
        for value in self.ALLOWED_VALUES:
            if value[0] == severity_priority:
                return value[1]
        raise ValueError("No severity with priority '%s'" % severity_priority)

    @property
    def priority(self):
        return self.value[0]

    def __unicode__(self):
        return self.value[1]

    def __cmp__(self, other):
        if isinstance(other, tuple):
            return cmp(self.priority, other[0])
        elif isinstance(other, Severity):
            return cmp(self.priority, other.priority)
        raise ValueError("Cannot compare Severity with %s" % type(other))


class Messages(UserNotify):
    tag = "messages"

    def __init__(self, messages=None):
        super(Messages, self).__init__()
        self.messages = messages or []

    @staticmethod
    def from_element(element):
        messages = []
        for message_elem in element.iter(UserNotify.qual_tag(Message.tag)):
            messages.append(Message.from_element(message_elem))
        return Messages(messages)

    @property
    def key(self):
        return "messages"

    @property
    def restarts(self):
        return [m for m in self.messages
                if m.severity == Severity.RESTART]

    @property
    def new(self):
        # return messages that have not been displayed and restarts
        return [m for m in self.sorted_by_priority
                if not m.displayed or m.severity == Severity.RESTART]

    @property
    def sorted_by_priority(self):
        return sorted(self.messages, key=lambda x: x.severity.priority, reverse=True)


class Message(UserNotify):
    tag = "message"

    def __init__(self, message_id, body, severity, timestamp, sent=False, displayed=False):
        super(Message, self).__init__()
        self.id = message_id
        self.body = body or LocalizableTextValue()
        if isinstance(severity, Severity):
            self.severity = severity
        else:
            self.severity = Severity(severity)
        self.created_at = datetime.fromtimestamp(timestamp)
        self.sent = sent
        self.displayed = displayed

    @staticmethod
    def from_element(element):
        xml_lang_attr = "{http://www.w3.org/XML/1998/namespace}lang"

        body_els = element.findall(Message.qual_tag("body"))
        body = LocalizableTextValue()
        for body_el in body_els:
            lang = body_el.get(xml_lang_attr)
            body.set_translation(lang, body_el.text)

        message_id = element.find(Message.qual_tag("id")).text
        severity = element.find(Message.qual_tag("severity")).text
        timestamp = int(element.find(Message.qual_tag("timestamp")).text)
        sent = element.find(Message.qual_tag("sent")) is not None
        displayed = element.find(Message.qual_tag("displayed")) is not None

        return Message(message_id, body, severity, timestamp, sent, displayed)

    @cached_property
    def escaped_body(self):
        escaped = LocalizableTextValue()
        for k, v in self.body.iteritems():
            escaped[k] = html_escape(self.body[k]).replace("\n", "<br />")
        return escaped

    @property
    def key(self):
        return self.id

    @property
    def requires_restart(self):
        return self.severity == Severity.RESTART

    def __unicode__(self):
        return unicode(self.body)

####################################################################################################
ET.register_namespace("user-notify", UserNotify.NS_URI)
