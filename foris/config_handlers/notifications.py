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

from foris import fapi, validators
from foris.form import (
    Password, Textbox, Dropdown, Checkbox, Radio, Number, Email, Time,
)
from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, _

from .base import BaseConfigHandler


class NotificationsHandler(BaseConfigHandler):
    userfriendly_title = gettext("Notifications")

    def get_form(self):
        data = current_state.backend.perform("router_notifications", "get_settings")
        data["enable_smtp"] = data["emails"]["enabled"]
        data["use_turris_smtp"] = "1" if data["emails"]["smtp_type"] == "turris" else "0"
        data["to"] = " ".join(data["emails"]["common"]["to"])
        data["sender_name"] = data["emails"]["smtp_turris"]["sender_name"]
        data["severity"] = data["emails"]["common"]["severity_filter"]
        data["news"] = data["emails"]["common"]["send_news"]
        data["from"] = data["emails"]["smtp_custom"]["from"]
        data["server"] = data["emails"]["smtp_custom"]["host"]
        data["port"] = data["emails"]["smtp_custom"]["port"]
        data["security"] = data["emails"]["smtp_custom"]["security"]
        data["username"] = data["emails"]["smtp_custom"]["username"]
        data["password"] = data["emails"]["smtp_custom"]["password"]
        data["delay"] = data["reboots"]["delay"]
        data["reboot_time"] = data["reboots"]["time"]

        if self.data:
            # Update from post
            data.update(self.data)

        notifications_form = fapi.ForisForm("notifications", data)

        notifications = notifications_form.add_section(
            name="notifications", title=_("Notifications settings"))
        # notifications settings
        notifications.add_field(
            Checkbox, name="enable_smtp", label=_("Enable notifications"), default=False)

        notifications.add_field(
            Radio,
            name="use_turris_smtp",
            label=_("SMTP provider"),
            default="0",
            args=(("1", _("Turris")), ("0", _("Custom"))),
            hint=_("If you set SMTP provider to \"Turris\", the servers provided to members of the "
                   "Turris project would be used. These servers do not require any additional "
                   "settings. If you want to set your own SMTP server, please select \"Custom\" "
                   "and enter required settings.")
        ).requires("enable_smtp", True)

        notifications.add_field(
            Textbox,
            name="to",
            label=_("Recipient's email"),
            hint=_("Email address of recipient. Separate multiple addresses by spaces."),
            required=True
        ).requires("enable_smtp", True)

        # sender's name for CZ.NIC SMTP only
        notifications.add_field(
            Textbox,
            name="sender_name",
            label=_("Sender's name"),
            hint=_("Name of the sender - will be used as a part of the "
                   "sender's email address before the \"at\" sign."),
            validators=[
                validators.RegExp(
                    _("Sender's name can contain only alphanumeric characters, dots "
                      "and underscores."),
                    r"^[0-9a-zA-Z_\.-]+$"
                )
            ],
            required=True
        ).requires("enable_smtp", True).requires("use_turris_smtp", "1")

        SEVERITY_OPTIONS = (
            (1, _("Reboot is required")),
            (2, _("Reboot or attention is required")),
            (3, _("Reboot or attention is required or update was installed")),
        )
        notifications.add_field(
            Dropdown, name="severity", label=_("Importance"),
            args=SEVERITY_OPTIONS, default=1
        ).requires("enable_smtp", True)
        notifications.add_field(
            Checkbox, name="news", label=_("Send news"),
            hint=_("Send emails about new features."),
            default=True
        ).requires("enable_smtp", True)

        # SMTP settings (custom server)
        smtp = notifications_form.add_section(name="smtp", title=_("SMTP settings"))
        smtp.add_field(
            Email, name="from", label=_("Sender address (From)"),
            hint=_("This is the address notifications are send from."),
        required=True).requires("enable_smtp", True).requires("use_turris_smtp", "0")
        smtp.add_field(
            Textbox, name="server", label=_("Server address"),
        ).requires("enable_smtp", True).requires("use_turris_smtp", "0")
        smtp.add_field(
            Number, name="port", label=_("Server port"),
            validators=[validators.PositiveInteger()],
            required=True
        ).requires("enable_smtp", True).requires("use_turris_smtp", "0")

        SECURITY_OPTIONS = (
            ("none", _("None")),
            ("ssl", _("SSL/TLS")),
            ("starttls", _("STARTTLS")),
        )
        smtp.add_field(
            Dropdown, name="security", label=_("Security"), args=SECURITY_OPTIONS,
            default="none"
        ).requires("enable_smtp", True).requires("use_turris_smtp", "0")

        smtp.add_field(
            Textbox, name="username", label=_("Username"),
        ).requires("enable_smtp", True).requires("use_turris_smtp", "0")
        smtp.add_field(
            Password, name="password", label=_("Password"),
        ).requires("enable_smtp", True).requires("use_turris_smtp", "0")

        # reboot time
        reboot = notifications_form.add_section(
            name="reboot", title=_("Automatic restarts after software update"))
        reboot.add_field(
            Number, name="delay", label=_("Delay (days)"),
            hint=_("Number of days that must pass between receiving the request "
                   "for restart and the automatic restart itself."),
            validators=[validators.PositiveInteger(), validators.InRange(0, 10)],
            required=True
        )
        reboot.add_field(
            Time, name="reboot_time", label=_("Reboot time"),
            hint=_("Time of day of automatic reboot in HH:MM format."),
            validators=[validators.Time()],
            required=True
        )

        def notifications_form_cb(data):
            msg = {
                "reboots": {"delay": int(data["delay"]), "time": data["reboot_time"]},
                "emails": {"enabled": data["enable_smtp"]},
            }
            if data["enable_smtp"]:
                msg["emails"]["smtp_type"] = "turris" if data["use_turris_smtp"] == "1" \
                    else "custom"
                msg["emails"]["common"] = {
                    "to": data["to"].split(" "),
                    "severity_filter": int(data["severity"]),
                    "send_news": data["news"],
                }
                if msg["emails"]["smtp_type"] == "turris":
                    msg["emails"]["smtp_turris"] = {"sender_name": data["sender_name"]}
                elif msg["emails"]["smtp_type"] == "custom":
                    msg["emails"]["smtp_custom"] = {
                        "from": data["from"],
                        "host": data["server"],
                        "port": int(data["port"]),
                        "security": data["security"],
                        "username": data["username"],
                        "password": data["password"],
                    }

            res = current_state.backend.perform("router_notifications", "update_settings", msg)

            return "save_result", res  # store {"result": ...} to be used later...

        notifications_form.add_callback(notifications_form_cb)

        return notifications_form
