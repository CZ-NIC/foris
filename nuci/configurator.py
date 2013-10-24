import logging
import client

__all__ = ['add_config_update', 'commit']

logger = logging.getLogger("nuci.configurator")

config_updates = []
field_updates = {}


def add_config_update(yin_element):
    """Serves for altering more complicated structures in Nuci configuration
    (i.e. not key = value).

    :param yin_element:
    :return:
    """
    config_updates.append(yin_element)


def clean_updates():
    global config_updates, field_updates
    config_updates = []
    field_updates = {}


def commit():
    from xml.etree import cElementTree as ET
    logger.debug("Commiting changes.")
    for cu in config_updates:
        logger.debug("Commiting config update:\n%s" % ET.tostring(cu.get_xml()))
        client.edit_config(cu.get_xml())
    clean_updates()