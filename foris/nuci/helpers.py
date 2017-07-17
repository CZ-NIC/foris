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

from ncclient.operations import TimeoutExpiredError, RPCError

from foris import DEVICE_CUSTOMIZATION
from foris.utils.translators import _
from foris.state import nuci_cache

from .client import get as nuci_get, edit_config as nuci_edit_config
from .filters import foris_config
from .modules.user_notify import Severity
from .modules.uci_raw import parse_uci_bool, Uci, Config, Section, Option


def make_notification_title(notification):
    """
    Helper function for creating of human-readable notification title.

    :param notification: notification to create title for
    :return: translated string with notification title
    """
    notification_titles = {
        Severity.NEWS: _("News"),
        Severity.UPDATE: _("Update"),
        Severity.ERROR: _("Error"),
    }

    # minor abuse of gettext follows...
    locale_date = notification.created_at.strftime(_("%Y/%m/%d %H:%M:%S"))

    return _("%(notification)s from %(created_at)s") % dict(
        notification=notification_titles.get(notification.severity.value, _("Notification")),
        created_at=locale_date
    )


def contract_valid():
    """Read whether the contract related with the current router is valid from uci

    :return: whether the contract is still valid
    """
    if DEVICE_CUSTOMIZATION == "omnia":
        return False

    data = nuci_cache.get("foris.contract", 60 * 60)  # once per hour should be enought
    valid = data.find_child("foris.contract.valid")

    if not valid:  # valid record
        # valid record not found, assuming that the contract is still valid
        return True

    return parse_uci_bool(valid)


def read_uci_lang(default):
    """Read interface language saved in Uci config foris.settings.lang.

    :param default: returned if no language is set in the config
    :return: language code of interface language
    """
    data = nuci_get(filter=foris_config)
    lang = data.find_child("uci.foris.settings.lang")
    if lang is None:
        return default
    return lang.value


def write_uci_lang(lang):
    """Save interface language to foris.settings.lang.

    :param lang: language code to save
    :return: True on success, False otherwise
    """
    uci = Uci()
    # Foris language
    foris = Config("foris")
    uci.add(foris)
    server = Section("settings", "config")
    foris.add(server)
    server.add(Option("lang", lang))
    # LuCI language
    luci = Config("luci")
    uci.add(luci)
    main = Section("main", "core")
    luci.add(main)
    main.add(Option("lang", lang))
    try:
        nuci_edit_config(uci.get_xml())
        return True
    except (RPCError, TimeoutExpiredError):
        return False
