# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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


def unqualify(tag):
    index = tag.index("}")
    if index != -1:
        return tag[index+1:]
    return tag


class LocalizableTextValue(dict):
    """
    Object that can contain text string in multiple languages.

    Access the strings either by getting dictionary item with  desired
    language as key, e.g.:
        value["cs"]
    or by simply coercing value to string to get string in default language.
    """
    def __init__(self, text=None, default_lang="en"):
        if text:
            if isinstance(text, basestring):
                text = {default_lang: text}
            elif not isinstance(text, dict):
                raise ValueError("Text must be either dict or string.")
        else:
            text = {}
        self.default_lang = default_lang

        # initialize dict and update values
        super(LocalizableTextValue, self).__init__()
        self.update(text)

    def __getitem__(self, item):
        try:
            return super(LocalizableTextValue, self).__getitem__(item)
        except KeyError:
            return super(LocalizableTextValue, self).__getitem__(self.default_lang)

    def __str__(self):
        return self[self.default_lang]

    def set_translation(self, language, text):
        """
        Set value for a given language.

        :param language: language of message
        :param text: localized text
        """
        self[language] = text
