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

from foris.caches import nuci_cache
from foris.state import info
from foris.utils import WIZARD_NEXT_STEP_ALLOWED_KEY
from foris.utils.translators import _

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
    if info.device_customization == "omnia":
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
    lang = lang.value if lang else default

    # Update info variable
    info.update_lang(lang)

    return lang


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
    if info.app == "config":
        # LuCI language (only in config app)
        luci = Config("luci")
        uci.add(luci)
        main = Section("main", "core")
        luci.add(main)
        main.add(Option("lang", lang))
    try:
        nuci_edit_config(uci.get_xml())

        # Update info variable
        info.update_lang(lang)

        return True
    except (RPCError, TimeoutExpiredError):
        return False


def mark_wizard_finished_session(session):
    """Mark wizard as finished in session.

    :param session: session
    :type session: foris.middleware.sessions.SessionProxy

    :return: None
    """
    session["wizard_finished"] = True
    session.save()


def allow_next_step_session(session, step_number):
    """
    Allow step in session.

    :param session: session
    :type session: foris.middleware.sessions.SessionProxy

    :param step_number: step to allow
    """
    # update session variable
    session[WIZARD_NEXT_STEP_ALLOWED_KEY] = step_number
    session.save()


def get_wizard_progress(session):
    """Get number of the allowed step and information whether wizard was finished
    from session, or from Foris Uci config if session is empty.

    Updates session variables of max allowed step and wizard finished flag if value was
    retrieved from Uci config.

    :param session: session
    :type session: foris.middleware.sessions.SessionProxy
    :return: step number of last allowed step (default is 1) and boolean flag - wizard is finished
    :rtype: tuple(int, bool)
    """
    allowed_sess = session.get(WIZARD_NEXT_STEP_ALLOWED_KEY, None)
    is_finished = session.get("wizard_finished", False)
    try:
        if not allowed_sess:
            data = nuci_get(filter=foris_config)
            next_step_option = data.find_child(
                "uci.foris.wizard.%s" % WIZARD_NEXT_STEP_ALLOWED_KEY)
            is_finished_option = data.find_child("uci.foris.wizard.finished")
            next_step_allowed = int(next_step_option.value) if next_step_option else 1
            is_finished = bool(int(is_finished_option.value)) if is_finished_option else False
            # write to session so we don't have to check config later
            allow_next_step_session(session, next_step_allowed)
            if is_finished:
                mark_wizard_finished_session(session)
            return next_step_allowed, is_finished
        return int(allowed_sess), is_finished
    except ValueError:
        return 1, False
