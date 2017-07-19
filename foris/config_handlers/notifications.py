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
from foris.nuci import filters
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option, List, Value
from foris.utils.translators import gettext_dummy as gettext, _

from .base import BaseConfigHandler


class NotificationsHandler(BaseConfigHandler):
    userfriendly_title = gettext("Notifications")

    def get_form(self):
        notifications_form = fapi.ForisForm(
            "notifications", self.data,
            filter=filters.create_config_filter("user_notify")
        )

        notifications = notifications_form.add_section(name="notifications",
                                                       title=_("Notifications settings"))
        # notifications settings
        notifications.add_field(Checkbox, name="enable_smtp", label=_("Enable notifications"),
                                nuci_path="uci.user_notify.smtp.enable",
                                nuci_preproc=lambda val: bool(int(val.value)),
                                default=False)

        notifications.add_field(
            Radio,
            name="use_turris_smtp",
            label=_("SMTP provider"),
            default="0",
            args=(("1", _("Turris")), ("0", _("Custom"))),
            nuci_path="uci.user_notify.smtp.use_turris_smtp",
            hint=_("If you set SMTP provider to \"Turris\", the servers provided to members of the "
                   "Turris project would be used. These servers do not require any additional "
                   "settings. If you want to set your own SMTP server, please select \"Custom\" "
                   "and enter required settings."))\
            .requires("enable_smtp", True)

        notifications.add_field(
            Textbox,
            name="to",
            label=_("Recipient's email"),
            nuci_path="uci.user_notify.smtp.to",
            nuci_preproc=lambda x: " ".join(map(lambda value: value.content, x.children)),
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
            nuci_path="uci.user_notify.smtp.sender_name",
            validators=[validators.RegExp(_("Sender's name can contain only "
                                            "alphanumeric characters, dots "
                                            "and underscores."),
                                          r"^[0-9a-zA-Z_\.-]+$")],
            required=True
        )\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "1")

        SEVERITY_OPTIONS = (
            (1, _("Reboot is required")),
            (2, _("Reboot or attention is required")),
            (3, _("Reboot or attention is required or update was installed")),
        )
        notifications.add_field(Dropdown, name="severity", label=_("Importance"),
                                nuci_path="uci.user_notify.notifications.severity",
                                nuci_preproc=lambda val: int(val.value),
                                args=SEVERITY_OPTIONS, default=1)\
            .requires("enable_smtp", True)
        notifications.add_field(Checkbox, name="news", label=_("Send news"),
                                hint=_("Send emails about new features."),
                                nuci_path="uci.user_notify.notifications.news",
                                nuci_preproc=lambda val: bool(int(val.value)),
                                default=True)\
            .requires("enable_smtp", True)

        # SMTP settings (custom server)
        smtp = notifications_form.add_section(name="smtp", title=_("SMTP settings"))
        smtp.add_field(Email, name="from", label=_("Sender address (From)"),
                       hint=_("This is the address notifications are send from."),
                       nuci_path="uci.user_notify.smtp.from",
                       required=True)\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")
        smtp.add_field(
            Textbox, name="server", label=_("Server address"),
            nuci_path="uci.user_notify.smtp.server", required=True)\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")
        smtp.add_field(
            Number, name="port", label=_("Server port"),
            nuci_path="uci.user_notify.smtp.port",
            validators=[validators.PositiveInteger()],
            required=True) \
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")

        SECURITY_OPTIONS = (
            ("none", _("None")),
            ("ssl", _("SSL/TLS")),
            ("starttls", _("STARTTLS")),
        )
        smtp.add_field(Dropdown, name="security", label=_("Security"),
                       nuci_path="uci.user_notify.smtp.security",
                       args=SECURITY_OPTIONS, default="none") \
            .requires("enable_smtp", True).requires("use_turris_smtp", "0")

        smtp.add_field(Textbox, name="username", label=_("Username"),
                       nuci_path="uci.user_notify.smtp.username")\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")
        smtp.add_field(Password, name="password", label=_("Password"),
                       nuci_path="uci.user_notify.smtp.password")\
            .requires("enable_smtp", True)\
            .requires("use_turris_smtp", "0")

        # reboot time
        reboot = notifications_form.add_section(name="reboot",
                                                title=_("Automatic restarts after software update"))
        reboot.add_field(Number, name="delay", label=_("Delay (days)"),
                         hint=_("Number of days that must pass between receiving the request "
                                "for restart and the automatic restart itself."),
                         nuci_path="uci.user_notify.reboot.delay",
                         validators=[validators.PositiveInteger(),
                                     validators.InRange(0, 10)],
                         required=True)
        reboot.add_field(Time, name="reboot_time", label=_("Reboot time"),
                         hint=_("Time of day of automatic reboot in HH:MM format."),
                         nuci_path="uci.user_notify.reboot.time",
                         validators=[validators.Time()],
                         required=True)

        def notifications_form_cb(data):
            uci = Uci()
            user_notify = Config("user_notify")
            uci.add(user_notify)

            smtp = Section("smtp", "smtp")
            user_notify.add(smtp)
            smtp.add(Option("enable", data['enable_smtp']))

            reboot = Section("reboot", "reboot")
            user_notify.add(reboot)
            reboot.add(Option("time", data['reboot_time']))
            reboot.add(Option("delay", data['delay']))

            if data['enable_smtp']:
                smtp.add(Option("use_turris_smtp", data['use_turris_smtp']))
                if data['use_turris_smtp'] == "0":
                    smtp.add(Option("server", data['server']))
                    smtp.add(Option("port", data['port']))
                    smtp.add(Option("username", data['username']))
                    smtp.add(Option("password", data['password']))
                    smtp.add(Option("security", data['security']))
                    smtp.add(Option("from", data['from']))
                else:
                    smtp.add(Option("sender_name", data['sender_name']))
                to = List("to")
                for i, to_item in enumerate(data['to'].split(" ")):
                    if to_item:
                        to.add(Value(i, to_item))
                smtp.add_replace(to)
                # notifications section
                notifications = Section("notifications", "notifications")
                user_notify.add(notifications)
                notifications.add(Option("severity", data['severity']))
                notifications.add(Option("news", data['news']))

            return "edit_config", uci

        notifications_form.add_callback(notifications_form_cb)

        return notifications_form
