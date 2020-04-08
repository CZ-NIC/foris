# coding=utf-8

# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2017 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

import csv
import logging
import pathlib
import re
from datetime import datetime, timedelta

import bottle
from bottle import html_escape
from foris.utils.translators import _

from .routing import external_route


def shorten_text(text, max_chars, etc="..."):
    """ Shortens text. "Very long text" -> "Very long..."
    """
    if len(text) > max_chars:
        return text[: max_chars - len(etc)] + etc
    return text


def external_url(path):
    return external_route(path)


def remove_html_tags(text):
    return re.sub(r"<[^>]*>", "", text)


def translate_datetime(datetime_instance, default="%Y/%m/%d %H:%M:%S"):
    """ Tries to "translate" the datetime.

    This functions should handle e.g. conversions between US / EU date format
    according to localized translation. So these formats were added to be translated.
    Unfortunatelly some translators used non-asci characters to format the date.
    That would raise an exception and this function handles that by adding a fallback format.

    :param datetime_instance: date to be formatted
    :type datetime_instance: datetime.datetime
    :param default: default format
    :type default: str

    :returns: formatted date
    :rtype: str
    """

    try:
        return datetime_instance.strftime(_("%Y/%m/%d %H:%M:%S"))
    except UnicodeEncodeError:
        # Unicode characters in translated format -> fallback to default
        return datetime_instance.strftime(default)


def make_notification_title(notification):
    """
    Helper function for creating of human-readable notification title.

    :param notification: notification to create title for
    :return: translated string with notification title
    """
    notification_titles = {"news": _("News"), "update": _("Update"), "error": _("Error")}

    # minor abuse of gettext follows...
    locale_date = translate_datetime(
        datetime.strptime(notification["created_at"], "%Y-%m-%dT%H:%M:%S")
    )

    return _("%(notification)s from %(created_at)s") % dict(
        notification=notification_titles.get(notification["severity"], _("Notification")),
        created_at=locale_date,
    )


def transform_notification_message(msg):
    return html_escape(msg).replace("\n", "<br />")


def prepare_approval_item_message(approval_item, show_operation=True):
    if approval_item["op"] == "install":
        return ((_("Install") + " ") if show_operation else "") + u"%s (%s)" % (
            approval_item["name"],
            approval_item["new_ver"],
        )
    elif approval_item["op"] == "remove":
        return ((_("Uninstall") + " ") if show_operation else "") + u"%s" % (approval_item["name"],)
    elif approval_item["op"] == "upgrade":
        return ((_("Upgrade") + " ") if show_operation else "") + "%s (%s)" % (
            approval_item["name"],
            approval_item["new_ver"],
        )
    elif approval_item["op"] == "downgrade":
        return ((_("Downgrade") + " ") if show_operation else "") + "%s (%s)" % (
            approval_item["name"],
            approval_item["new_ver"],
        )


def increase_time(orig_time, days=0, hours=0, minutes=0, seconds=0):
    return orig_time + timedelta(days, hours, minutes, seconds)


REFORIS_LINKS_FILE = pathlib.Path("/usr/share/foris/reforis-links.csv")

logger = logging.getLogger(__file__)


def reforis_redirect(request: bottle.BaseRequest) -> str:
    if REFORIS_LINKS_FILE.exists():
        try:
            with REFORIS_LINKS_FILE.open() as f:
                reader = csv.reader(f)
                for from_path, to_path in reader:
                    if request.path.endswith(from_path):
                        return to_path
        except Exception:
            logger.warning("Failed to read reforis links file '%s'", REFORIS_LINKS_FILE)

    else:
        logger.warning("Reforis links file '%s' does not exist.", REFORIS_LINKS_FILE)

    return ""
