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

import re

from .routing import external_route
from foris.utils.translators import _


def shorten_text(text, max_chars, etc="..."):
    """ Shortens text. "Very long text" -> "Very long..."
    """
    if len(text) > max_chars:
        return text[:max_chars - len(etc)] + etc
    return text


def external_url(path):
    return external_route(path)


def remove_html_tags(text):
    return re.sub(r'<[^>]*>', '', text)


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
