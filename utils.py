import logging
from xml.etree import cElementTree as ET


logger = logging.getLogger("kruci.utils")


class Lazy(object):
    def __init__(self, func):
        self.func = func
        self.value = None

    def __call__(self):
        if self.value is None:
            self.value = self.func()
        return self.value

    def __getattr__(self, item):
        if self.value is None:
            self.value = self.func()
        return getattr(self.value, item)


def print_model(model):
    import copy
    toprint = copy.deepcopy(model.get_tree())
    indent(toprint)
    data = ET.tostring(toprint)
    logger.debug(data)
    return data


def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level+1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i