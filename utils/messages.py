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
    def __init__(self, text, level, extra_classes=None):
        self.text = text
        self.level = level
        self.extra_classes = extra_classes

    @property
    def classes(self):
        if self.extra_classes:
            return " ".join([self.level[1], self.extra_classes])
        return self.level[1]


def get_messages(level=None, min_level=None):
    def should_show():
        if level and msg.level[0] == level[0]:
            return True
        elif min_level and msg.level[0] >= min_level[0]:
            return True
        elif not level and not min_level:
            return True
        return False

    session = bottle.request.environ['beaker.session']
    messages = session.get(_SESSION_KEY, [])
    all_messages = messages[:]
    for msg in all_messages:
        if should_show():
            messages.remove(msg)
            session[_SESSION_KEY] = messages
            yield msg


def add_message(text, level=INFO, extra_classes=None):
    session = bottle.request.environ['beaker.session']
    messages = session.get(_SESSION_KEY, [])
    messages.append(Message(text, level, extra_classes))
    session[_SESSION_KEY] = messages


def set_template_defaults(template):
    template.defaults['get_messages'] = get_messages
    template.defaults['get_alert_messages'] = functools.partial(get_messages, min_level=WARNING)