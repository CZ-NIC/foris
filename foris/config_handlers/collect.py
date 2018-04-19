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

from foris import fapi
from foris.form import Checkbox, MultiCheckbox

from foris.form import Email
from foris.nuci import client, filters
from foris.nuci.modules.uci_raw import (
    Uci, Config, Section, List, Value
)
from foris.utils.translators import gettext_dummy as gettext, _
from foris.state import current_state

from .base import BaseConfigHandler, logger


class UcollectHandler(BaseConfigHandler):
    userfriendly_title = gettext("uCollect")

    def get_form(self):
        data = current_state.backend.perform("data_collect", "get_honeypots", {})

        # convert data from backend to form data
        data["services"] = []
        for minipot in data["minipots"]:
            if data["minipots"][minipot]:
                data["services"].append(minipot)
        del data["minipots"]

        if self.data:
            # Update from post
            if "log_credentials" in self.data:
                data["log_credentials"] = self.data["log_credentials"]

            # services is a multifield which has to be handled differently
            data["services"] = [e for e in self.data.getall("services[]") if e]

        ucollect_form = fapi.ForisForm("ucollect", data)
        fakes = ucollect_form.add_section(
            name="fakes",
            title=_("Emulated services"),
            description=_("One of uCollect's features is emulation of some commonly abused "
                          "services. If this function is enabled, uCollect is listening for "
                          "incoming connection attempts to these services. Enabling of the "
                          "emulated services has no effect if another service is already "
                          "listening on its default port (port numbers are listed below).")
        )

        SERVICES_OPTIONS = (
            ("23tcp", _("Telnet (23/TCP)")),
            ("2323tcp", _("Telnet - alternative port (2323/TCP)")),
            ("80tcp", _("HTTP (80/TCP)")),
            ("3128tcp", _("Squid HTTP proxy (3128/TCP)")),
            ("8123tcp", _("Polipo HTTP proxy (8123/TCP)")),
            ("8080tcp", _("HTTP proxy (8080/TCP)")),
        )

        fakes.add_field(
            MultiCheckbox,
            name="services",
            label=_("Emulated services"),
            args=SERVICES_OPTIONS,
            multifield=True,
        )

        fakes.add_field(
            Checkbox,
            name="log_credentials",
            label=_("Collect credentials"),
            hint=_("If this option is enabled, user names and passwords are collected "
                   "and sent to server in addition to the IP address of the client."),
        )

        def ucollect_form_cb(data):
            msg = {
                "log_credentials": data["log_credentials"],
                "minipots": {k: k in data["services"] for k in dict(SERVICES_OPTIONS)}
            }
            res = current_state.backend.perform("data_collect", "set_honeypots", msg, False)
            res = res if res else {"result": False}  # Set result false when an exception is raised
            return "save_result", res  # store {"result": ...} to be used later...

        ucollect_form.add_callback(ucollect_form_cb)

        return ucollect_form


class CollectionToggleHandler(BaseConfigHandler):
    userfriendly_title = gettext("Data collection")

    def get_form(self):
        data = current_state.backend.perform("data_collect", "get", {})
        if self.data and "enable" in self.data:
            data["enable"] = self.data["enable"]
        else:
            data["enable"] = data["agreed"]

        form = fapi.ForisForm(
            "enable_collection", data, filter=filters.create_config_filter("updater"))

        section = form.add_section(
            name="collection_toggle", title=_(self.userfriendly_title),
        )
        section.add_field(
            Checkbox, name="enable", label=_("Enable data collection"),
            preproc=lambda val: bool(int(val))
        )

        def form_cb(data):
            data = current_state.backend.perform(
                "data_collect", "set", {"agreed": data["enable"]})
            return "save_result", data  # store {"result": ...} to be used later...

        def adjust_lists_cb(data):
            uci = Uci()
            # All enabled lists
            enabled_lists = map(lambda x: x.content,
                                form.nuci_config.find_child("uci.updater.pkglists.lists").children)
            # Lists that do not need agreement
            enabled_no_agree = filter(lambda x: not x.startswith("i_agree_"), enabled_lists)
            # Lists that need agreement
            enabled_i_agree = filter(lambda x: x.startswith("i_agree_"), enabled_lists)

            # Always install lists that do not need agreement - create a copy of the list
            installed_lists = enabled_no_agree[:]
            logger.warning("no agree: %s", enabled_no_agree)
            logger.warning("installed: %s", installed_lists)
            if data.get("enable", False):
                # Include i_agree lists if user agreed with EULA
                installed_lists.extend(enabled_i_agree)
                # Add main data collection list if it's not present
                logger.warning(installed_lists)
                logger.warning("i_agree_datacollect" not in installed_lists)
                logger.warning("i_agree_datacollect" in installed_lists)
                if "i_agree_datacollect" not in installed_lists:
                    logger.warning("appending")
                    installed_lists.append("i_agree_datacollect")
            logger.warning("saving %s", installed_lists)
            # Reconstruct list of package lists
            updater = uci.add(Config("updater"))
            pkglists = updater.add(Section("pkglists", "pkglists"))
            lists = List("lists")
            for i, name in enumerate(installed_lists):
                lists.add(Value(i, name))

            # If there's anything to add, replace the list, otherwise remove it completely
            if len(installed_lists) > 0:
                pkglists.add_replace(lists)
            else:
                pkglists.add_removal(lists)

            return "edit_config", uci

        def run_updater_cb(data):
            logger.info("Checking for updates.")
            client.check_updates()
            return "none", None

        form.add_callback(form_cb)
        form.add_callback(adjust_lists_cb)
        form.add_callback(run_updater_cb)

        return form


class RegistrationCheckHandler(BaseConfigHandler):
    """
    Handler for checking of the registration status and assignment to a queried email address.
    """

    userfriendly_title = gettext("Data collection")

    def get_form(self):
        form = fapi.ForisForm(
            "registration_check", self.data, filter=filters.create_config_filter("foris")
        )
        main_section = form.add_section(name="check_email", title=_(self.userfriendly_title))
        main_section.add_field(
            Email, name="email", label=_("Email")
        )

        def form_cb(data):
            data = current_state.backend.perform(
                "data_collect", "get_registered",
                {"email": data.get("email"), "language": current_state.language}
            )
            error = None
            registration_number = None
            url = None
            if data["status"] == "unknown":
                error = _("Failed to query the server.")
            elif data["status"] == "not_valid":
                error = _("Failed to verify the router's registration.")
            elif data["status"] in ["free", "foreign"]:
                url = data["url"]
                registration_number = data["registration_number"]

            return "save_result", {
                'success': data["status"] not in ["unknown", "not_valid"],
                'status': data["status"],
                'error': error,
                'url': url,
                'registration_number': registration_number,
            }

        form.add_callback(form_cb)
        return form
