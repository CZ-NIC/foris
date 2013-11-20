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
