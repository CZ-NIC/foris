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

import collections
import gettext
import os

from jinja2.ext import InternationalizationExtension

from foris import BASE_DIR
from foris.langs import translations
from foris.state import current_state

# read locale directory
locale_directory = os.path.join(BASE_DIR, "locale")


class _LangDict(collections.OrderedDict):
    def __missing__(self, key):
        # return english translation if missing key
        return super(_LangDict, self).__getitem__("en")


translations = _LangDict(
    (e, gettext.translation("messages", locale_directory, languages=[e], fallback=True))
    for e in translations
)


class SimpleDelayedTranslator(object):

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return gettext(self.text)

    def __unicode__(self):
        return gettext(self.text)


gettext = lambda x: translations[current_state.language].gettext(x)
ngettext = lambda singular, plural, n: \
    translations[current_state.language].ngettext(singular, plural, n)
gettext_dummy = lambda x: SimpleDelayedTranslator(x)

_ = gettext


def set_current_language(language):
    """Save interface language to foris.settings.lang.

    :param lang: language code to save
    :return: True on success, False otherwise
    """
    if current_state.backend.perform(
            "web", "set_language", {"language": language})["result"]:
        # Update info variable
        current_state.update_lang(language)
        return True

    return False


# for jinja template
class ForisInternationalizationExtension(InternationalizationExtension):
    def __init__(self, environment):
        super(ForisInternationalizationExtension, self).__init__(environment)
        self._install_callables(gettext, ngettext)


i18n = ForisInternationalizationExtension
