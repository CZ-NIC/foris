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
    logger.debug("Commiting changes.")
    client.edit_config_multiple([cu.get_xml() for cu in config_updates])
    clean_updates()