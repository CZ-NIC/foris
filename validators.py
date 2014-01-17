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

from foris import gettext as _

PARAM_DELIMITER = "|"
logger = logging.getLogger(__name__)


class Validator(object):
    js_validator = None

    def __deepcopy__(self, memo):
        return copy.copy(self)

    def __init__(self, msg, test):
        self.msg = msg
        self.test = test
        self.js_validator_params = None

    def valid(self, value):
        try:
            return self.test(value)
        except:
            return False


class RegExp(Validator):
    def __init__(self, msg, reg_exp):
        self.reg_exp = re.compile(reg_exp)
        super(RegExp, self).__init__(msg, lambda val: bool(self.reg_exp.match(val)))

    def valid(self, value):
        return bool(self.reg_exp.match(value))


class NotEmpty(Validator):
    js_validator = ("notblank", "true")

    def __init__(self):
        super(NotEmpty, self).__init__(_("This field is required."), bool)


class IPv4(Validator):
    js_validator = ("type", "ipv4")

    def __init__(self):
        super(IPv4, self).__init__(_("Not a valid IPv4 address."), None)

    def valid(self, value):
        import socket
        try:
            socket.inet_pton(socket.AF_INET, value)
            return True
        except socket.error:
            pass
        return False


class IPv6(Validator):
    js_validator = ("type", "ipv6")

    def __init__(self):
        super(IPv6, self).__init__(_("Not a valid IPv6 address."), None)

    def valid(self, value):
        import socket
        try:
            socket.inet_pton(socket.AF_INET6, value)
            return True
        except Exception:
            pass
        return False


class IPv6Prefix(Validator):
    js_validator = ("type", "ipv6prefix")

    def __init__(self):
        super(IPv6Prefix, self).__init__(_("Not a valid IPv6 prefix."), None)

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


class Integer(RegExp):
    js_validator = ("type", "digits")

    def __init__(self):
        super(Integer, self).__init__(_("Is not a number."), r"\d+")


class MacAddress(RegExp):
    js_validator = ("type", "macaddress")

    def __init__(self):
        super(MacAddress, self).__init__(_("MAC address is not valid."), r"([a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2}")


class InRange(Validator):
    js_validator = "range"

    def __init__(self, low, high):
        test = lambda val: val in range(low, high)
        super(InRange, self).__init__(_("Not in a valid range %(low)s - %(high)s.") % dict(low=low, high=high), test)
        self.js_validator_params = "[%s,%s]" % (low, high)


class LenRange(Validator):
    js_validator = "rangelength"

    def __init__(self, low, high):
        test = lambda val: low <= len(val) <= high
        super(LenRange, self).__init__(_("Length must be from %(low)s to %(high)s characters.") % dict(low=low, high=high), test)
        self.js_validator_params = "[%s,%s]" % (low, high)


class FieldsEqual(Validator):
    # TODO: migrate to parsley
    js_validator = "eqfields"
    
    def __init__(self, field1, field2, message):
        super(FieldsEqual, self).__init__(message, lambda data: data[field1] == data[field2])
        self.js_validator_params = PARAM_DELIMITER.join([field1, field2, message])


def validators_as_data_dict(validators):
    data = {}
    for v in validators:
        if v.js_validator:
            if isinstance(v.js_validator, tuple):
                data["parsley-%s" % v.js_validator[0]] = v.js_validator[1]
            elif v.js_validator_params:
                data["parsley-%s" % v.js_validator] = v.js_validator_params
            else:
                logger.warning("Uknown JS validator: %s" % v.js_validator)
    return data