import copy
import re


class Validator:
    def __deepcopy__(self, memo):
        return copy.copy(self)

    def __init__(self, msg, test, jstest=None):
        self.msg = msg
        self.test = test
        self.jstest = jstest

    def valid(self, value):
        try:
            return self.test(value)
        except:
            return False


class RegExp(Validator):
    def __init__(self, msg, reg_exp):
        self.rexp = re.compile(reg_exp)
        Validator.__init__(self, msg, lambda val: bool(self.rexp.match(val)))

    def valid(self, value):
        return bool(self.rexp.match(value))


class NotEmpty(Validator):
    def __init__(self):
        Validator.__init__(self, "This field is required.", bool)


class IPv4(RegExp):
    def __init__(self):
        RegExp.__init__(self, "Not a valid IPv4 address.", r"(\d{1,3}\.){3}\d{1,3}")


class Integer(RegExp):
    def __init__(self):
        RegExp.__init__(self, "Is not a number.", r"\d+")


class MacAddress(RegExp):
    def __init__(self):
        RegExp.__init__(self, "MAC address is not valid.", r"([a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2}")


class InRange(Validator):
    def __init__(self, low, high):
        test = lambda val: val in range(low, high)
        Validator.__init__(self, "Not in a valid range %s - %s." % (low, high), test)


class LenRange(Validator):
    def __init__(self, low, high):
        test = lambda val: low <= len(val) <= high
        Validator.__init__(self, "Length must be from %s to %s characters." % (low, high), test)


class FieldsEqual(Validator):
    def __init__(self, field1, field2, message):
        Validator.__init__(self, message, lambda data: data[field1] == data[field2])