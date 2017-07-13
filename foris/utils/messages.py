import functools
import bottle
import logging

logger = logging.getLogger(__name__)

_SESSION_KEY = '_messages'

# tuple of (priority, level_name)
INFO = (0, "info")
SUCCESS = (10, "success")
WARNING = (20, "warning")
ERROR = (30, "error")


class Message(object):
    def __init__(self, text, level, extra_classes=[]):
        """
        Create new message instance.

        :param text: text of the message
        :param level: severity level
        :param extra_classes: extra classes of message
        """
        self.text = text
        self.level = level
        self.extra_classes = extra_classes

    def to_json(self):
        return {
            "text": self.text,
            "level": self.level,
            "extra_classes": self.extra_classes,
        }

    @staticmethod
    def from_json(json):
        return Message(json["text"], json["level"], json["extra_classes"])

    @property
    def classes(self):
        """
        Classes of the message.

        :return: space-separated list of classes
        """
        if self.extra_classes:
            return " ".join([self.level[1], self.extra_classes])
        return self.level[1]


def get_messages(level=None, min_level=None):
    """
    Generator function yielding messages, optionally filtered by severity level.

    :param level: get messages with exact level
    :param min_level: get messages with level specified or higher
    """
    def should_show():
        if level and msg.level[0] == level[0]:
            return True
        elif min_level and msg.level[0] >= min_level[0]:
            return True
        elif not level and not min_level:
            return True
        return False

    session = bottle.request.environ['foris.session']
    messages = session.get(_SESSION_KEY, [])
    all_messages = messages[:]
    for msg in all_messages:
        if should_show():
            messages.remove(msg)
            session[_SESSION_KEY] = messages
            yield Message.from_json(msg)


def info(text, extra_classes=[]):
    """
    Add new info message.

    :param text: text of the message
    :param extra_classes: extra classes of the message
    """
    add_message(text, INFO, extra_classes)


def success(text, extra_classes=[]):
    """
    Add new success message.

    :param text: text of the message
    :param extra_classes: extra classes of the message
    """
    add_message(text, SUCCESS, extra_classes)


def warning(text, extra_classes=[]):
    """
    Add new warning message.

    :param text: text of the message
    :param extra_classes: extra classes of the message
    """
    add_message(text, WARNING, extra_classes)


def error(text, extra_classes=[]):
    """
    Add new error message.

    :param text: text of the message
    :param extra_classes: extra classes of the message
    """
    add_message(text, ERROR, extra_classes)


def add_message(text, level=INFO, extra_classes=[]):
    """
    Add new message.

    :param text: text of the message
    :param level: severity level
    :param extra_classes: extra classes of the message
    """
    session = bottle.request.environ['foris.session']
    messages = session.get(_SESSION_KEY, [])
    messages.append(Message(text, level, extra_classes).to_json())
    session[_SESSION_KEY] = messages


def set_template_defaults(template):
    """
    Add template functions as template defaults to supplied Bottle template
    adapter.

    :param template: Bottle template adapter - class inheriting from BaseTemplate
    """
    template.defaults['get_messages'] = get_messages
    template.defaults['get_alert_messages'] = functools.partial(get_messages, min_level=WARNING)
