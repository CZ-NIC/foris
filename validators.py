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

import copy
import logging
import re

from foris import ugettext as _
import form

logger = logging.getLogger(__name__)


class Validator(object):
    js_validator = None
    validate_with_context = False  # gets dict of data instead of single value if True

    def __deepcopy__(self, memo):
        return copy.copy(self)

    def __init__(self, msg):
        self.msg = msg
        self.js_validator_params = None
        self.extra_data = {}

    def valid(self, value):
        raise NotImplementedError


class RegExp(Validator):
    def __init__(self, msg, reg_exp):
        self.reg_exp = re.compile(reg_exp)
        super(RegExp, self).__init__(msg)
        self.js_validator = ("regexp", reg_exp)
        self.extra_data['parsley-error-message'] = msg

    def valid(self, value):
        return bool(self.reg_exp.match(value or ""))


class NotEmpty(Validator):
    js_validator = ("notblank", "true")

    def __init__(self):
        super(NotEmpty, self).__init__(_("This field is required."))

    def valid(self, value):
        return bool(value)


class IPv4(Validator):
    js_validator = ("extratype", "ipv4")

    def __init__(self):
        super(IPv4, self).__init__(_("Not a valid IPv4 address."))

    def valid(self, value):
        import socket
        try:
            socket.inet_pton(socket.AF_INET, value)
            return True
        except socket.error:
            pass
        return False


class IPv4Netmask(Validator):
    js_validator = ("extratype", "ipv4netmask")

    def __init__(self):
        super(IPv4Netmask, self).__init__(_("Not a valid IPv4 netmask address."))

    def valid(self, value):
        """The netmask must start with an uninterrupted sequence of 1s in its bit
        representation and not contain any 1s after the first zero."""
        import socket
        try:
            addr = socket.inet_aton(value)
        except socket.error:
            return False
        was_zero = False
        for byte in addr:
            for i in range(8):
                if not (ord(byte) & 1 << (7-i)):
                    was_zero = True
                elif was_zero:  # 1 and we have seen zero already
                    return False
        return True


class IPv6(Validator):
    js_validator = ("extratype", "ipv6")

    def __init__(self):
        super(IPv6, self).__init__(_("Not a valid IPv6 address."))

    def valid(self, value):
        import socket
        try:
            socket.inet_pton(socket.AF_INET6, value)
            return True
        except Exception:
            pass
        return False


class AnyIP(Validator):
    js_validator = ("extratype", "anyip")

    def __init__(self):
        super(AnyIP, self).__init__(_("This is not a valid IPv4 or IPv6 address."))

    def valid(self, value):
        import socket
        try:
            socket.inet_pton(socket.AF_INET, value)
            return True
        except Exception:
            try:
                socket.inet_pton(socket.AF_INET6, value)
                return True
            except Exception:
                pass
        return False


class IPv6Prefix(Validator):
    js_validator = ("extratype", "ipv6prefix")

    def __init__(self):
        super(IPv6Prefix, self).__init__(_("This is not an IPv6 address with prefix length."))

    def valid(self, value):
        import socket
        try:
            address, length = value.split("/")
            length = int(length)
            socket.inet_pton(socket.AF_INET6, address)
            if length < 0 or length > 128:
                return False
            return True
        except Exception:
            pass
        return False


class PositiveInteger(Validator):
    js_validator = ("type", "digits")

    def __init__(self):
        super(PositiveInteger, self).__init__(_("Is not a number."))

    def valid(self, value):
        try:
            int(value or 0) >= 0
            return True
        except ValueError:
            return False


class Time(RegExp):
    def __init__(self):
        pattern = r"^([01][0-9]|2[0-3]):([0-5][0-9])$"
        super(Time, self).__init__(_("This is not valid time in HH:MM format."), pattern)
        self.js_validator = ("regexp", pattern)
        self.extra_data['parsley-error-message'] = self.msg


class MacAddress(Validator):
    js_validator = ("extratype", "macaddress")

    def __init__(self):
        super(MacAddress, self).__init__(_("MAC address is not valid."))
        self.extra_data['parsley-validation-minlength'] = '17'


class InRange(Validator):
    js_validator = "range"

    def __init__(self, low, high):
        self._low = low
        self._high = high
        super(InRange, self).__init__(_("Not in a valid range %(low)s - %(high)s.")
                                      % dict(low=low, high=high))
        self.js_validator_params = "[%s,%s]" % (low, high)

    def valid(self, value):
        try:
            val = int(value)
            return val in range(self._low, self._high + 1)
        except ValueError:
            return False


class LenRange(Validator):
    js_validator = "length"

    def __init__(self, low, high):
        self._low = low
        self._high = high
        super(LenRange, self).__init__(_("Length must be from %(low)s to %(high)s characters.")
                                       % dict(low=low, high=high))
        self.js_validator_params = "[%s,%s]" % (low, high)

    def valid(self, value):
        return self._low <= len(unicode(value.decode("utf8"))) <= self._high


class ByteLenRange(Validator):
    """
    Length range validator that takes each byte of string as a single character.
    """
    js_validator = "bytelength"

    def __init__(self, low, high):
        self._low = low
        self._high = high
        super(ByteLenRange, self).__init__(_("Length must be from %(low)s to %(high)s characters.")
                                           % dict(low=low, high=high))
        self.js_validator_params = "[%s,%s]" % (low, high)

    def valid(self, value):
        return self._low <= len(value.decode("utf8")) <= self._high


class EqualTo(Validator):
    js_validator = "equalto"
    validate_with_context = True

    def __init__(self, field1, field2, message):
        self._field1 = field1
        self._field2 = field2
        super(EqualTo, self).__init__(message)
        self.js_validator_params = "#%s" % (form.ID_TEMPLATE % field1)

    def valid(self, data):
        return data[self._field1] == data[self._field2]


class RequiredWithOtherFields(Validator):
    validate_with_context = True

    def __init__(self, fields, message):
        self._fields = fields
        super(RequiredWithOtherFields, self).__init__(message)

    def valid(self, data):
        fields_data = [data[field] for field in self._fields]

        if any(fields_data):
            return all(fields_data)
        return True


def validators_as_data_dict(validators):
    data = {}
    for v in validators:
        data.update(v.extra_data)
        if v.js_validator:
            if isinstance(v.js_validator, tuple):
                data["parsley-%s" % v.js_validator[0]] = v.js_validator[1]
            elif v.js_validator_params:
                data["parsley-%s" % v.js_validator] = v.js_validator_params
            else:
                logger.warning("Unknown JS validator: %s", v.js_validator)
    return data
