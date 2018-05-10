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

        form = fapi.ForisForm("enable_collection", data)

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

        form.add_callback(form_cb)

        return form


class RegistrationCheckHandler(BaseConfigHandler):
    """
    Handler for checking of the registration status and assignment to a queried email address.
    """

    userfriendly_title = gettext("Data collection")

    def get_form(self):
        form = fapi.ForisForm("registration_check", self.data)
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
