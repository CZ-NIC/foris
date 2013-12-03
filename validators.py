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
import re


PARAM_DELIMITER = "|"


class Validator:
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
        Validator.__init__(self, msg, lambda val: bool(self.reg_exp.match(val)))

    def valid(self, value):
        return bool(self.reg_exp.match(value))


class NotEmpty(Validator):
    js_validator = "notempty"

    def __init__(self):
        Validator.__init__(self, "This field is required.", bool)


class IPv4(RegExp):
    js_validator = "ipv4"

    def __init__(self):
        RegExp.__init__(self, "Not a valid IPv4 address.", r"(\d{1,3}\.){3}\d{1,3}")


class Integer(RegExp):
    js_validator = "integer"

    def __init__(self):
        RegExp.__init__(self, "Is not a number.", r"\d+")


class MacAddress(RegExp):
    js_validator = "macaddress"

    def __init__(self):
        RegExp.__init__(self, "MAC address is not valid.", r"([a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2}")


class InRange(Validator):
    js_validator = "inrange"

    def __init__(self, low, high):
        test = lambda val: val in range(low, high)
        Validator.__init__(self, "Not in a valid range %s - %s." % (low, high), test)
        self.js_validator_params = "%s%s%s" % (low, PARAM_DELIMITER, high)


class LenRange(Validator):
    js_validator = "lenrange"

    def __init__(self, low, high):
        test = lambda val: low <= len(val) <= high
        Validator.__init__(self, "Length must be from %s to %s characters." % (low, high), test)
        self.js_validator_params = "%s%s%s" % (low, PARAM_DELIMITER, high)


class FieldsEqual(Validator):
    js_validator = "eqfields"
    
    def __init__(self, field1, field2, message):
        Validator.__init__(self, message, lambda data: data[field1] == data[field2])
        self.js_validator_params = PARAM_DELIMITER.join([field1, field2, message])


def validators_as_data_dict(validators):
    data = {}
    data_validators = []
    for v in validators:
        if v.js_validator:
            data_validators.append("%s" % v.js_validator)
            params = v.js_validator_params
            if params:
                data['validator-%s' % v.js_validator] = params
    if data_validators:
        data['validators'] = " ".join(data_validators)
    return data