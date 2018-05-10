# coding=utf-8

# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

import copy

from foris import fapi, validators
from foris.form import Checkbox, Radio, RadioSingle, Number, Hidden
from foris.state import current_state
from foris.utils import contract_valid
from foris.utils.translators import gettext_dummy as gettext, _

from .base import BaseConfigHandler


class UpdaterHandler(BaseConfigHandler):
    userfriendly_title = gettext("Updater")

    APPROVAL_NO = "off"
    APPROVAL_TIMEOUT = "delayed"
    APPROVAL_NEEDED = "on"
    APPROVAL_DEFAULT = APPROVAL_NO
    APPROVAL_DEFAULT_DELAY = 24

    def __init__(self, *args, **kwargs):
        super(UpdaterHandler, self).__init__(*args, **kwargs)
        self.contract_valid = contract_valid()
        if not self.contract_valid:
            self.agreed_collect = current_state.backend.perform("data_collect", "get", {})["agreed"]
        else:
            self.agreed_collect = True

        self.backend_data = current_state.backend.perform(
            "updater", "get_settings", {"lang": current_state.language})
        # store setting required for rendering
        self.branch = self.backend_data["branch"]
        self.current_approval = self.backend_data["approval"]
        self.updater_enabled = self.backend_data["enabled"]
        self.approval_setting_status = self.backend_data["approval_settings"]["status"]
        self.approval_setting_delay = self.backend_data["approval_settings"].get(
            "delay", self.APPROVAL_DEFAULT_DELAY)

    def get_form(self):
        data = copy.deepcopy(self.backend_data)

        data["enabled"] = "1" if data["enabled"] else "0"
        data["approval_status"] = data["approval_settings"]["status"]
        if "delay" in data["approval_settings"]:
            data["approval_delay"] = data["approval_settings"]["delay"]
        for userlist in [e for e in data['user_lists'] if not e["hidden"]]:
            data["install_%s" % userlist["name"]] = userlist["enabled"]
        for lang in data["languages"]:
            data["language_%s" % lang["code"]] = lang["enabled"]

        if self.data:
            # Update from post
            data.update(self.data)
            self.updater_enabled = True if data["enabled"] == "1" else False
            self.approval_setting_status = data["approval_status"]
            self.approval_setting_delay = data.get("approval_delay", self.APPROVAL_DEFAULT_DELAY)

        form = fapi.ForisForm("updater", data)
        main_section = form.add_section(
            name="main",
            title=_(self.userfriendly_title),
            description=_("Updater is a service that keeps all TurrisOS "
                          "software up to date. Apart from the standard "
                          "installation, you can optionally select lists of "
                          "additional software that'd be installed on the "
                          "router. This software can be selected from the "
                          "following list. "
                          "Please note that only software that is part of "
                          "TurrisOS or that has been installed from a package "
                          "list is maintained by Updater. Software that has "
                          "been installed manually or using opkg is not "
                          "affected.")
        )
        main_section.add_field(
            Radio, name="enabled", label=_("I agree"), default="1",
            args=(("1", _("Use automatic updates (recommended)")),
                  ("0", _("Turn automatic updates off"))),
        )

        approval_section = main_section.add_section(name="approvals", title=_("Update approvals"))
        approval_section.add_field(
            RadioSingle, name=UpdaterHandler.APPROVAL_NO, group="approval_status",
            label=_("Automatic installation"),
            hint=_("Updates will be installed without user's intervention."),
            default=data["approval_status"],
        )

        approval_section.add_field(
            RadioSingle, name=UpdaterHandler.APPROVAL_TIMEOUT, group="approval_status",
            label=_("Delayed updates"),
            hint=_(
                "Updates will be installed with an adjustable delay. "
                "You can also approve them manually."
            ),
            default=data["approval_status"],
        )
        approval_section.add_field(
            Number, name="approval_delay", validators=[validators.InRange(1, 24 * 7)],
            default=UpdaterHandler.APPROVAL_DEFAULT_DELAY, min=1, max=24 * 7, required=True,
        ).requires(
            UpdaterHandler.APPROVAL_TIMEOUT, UpdaterHandler.APPROVAL_TIMEOUT
        ).requires(
            UpdaterHandler.APPROVAL_NO, UpdaterHandler.APPROVAL_TIMEOUT
        ).requires(
            UpdaterHandler.APPROVAL_NEEDED, UpdaterHandler.APPROVAL_TIMEOUT
        )

        approval_section.add_field(
            RadioSingle, name=UpdaterHandler.APPROVAL_NEEDED, group="approval_status",
            label=_("Update approval needed"),
            hint=_("You have to approve the updates, otherwise they won't be installed."),
            default=data["approval_status"],
        )

        package_lists_main = main_section.add_section(
            name="select_package_lists", title=None,
        )
        for userlist in [e for e in data['user_lists'] if not e["hidden"]]:
            package_lists_main.add_field(
                Checkbox, name="install_%s" % userlist["name"], label=userlist["title"],
                hint=userlist["msg"]
            ).requires("enabled", "1")

        language_lists_main = main_section.add_section(
            name="select_languages",
            title=_(
                "If you want to use other language than English you can select it from the "
                "following list:"
            )
        )
        for lang in data["languages"]:
            language_lists_main.add_field(
                Checkbox, name="language_%s" % lang["code"], label=lang["code"].upper())

        if self.backend_data["approval"]["present"]:
            # field for hidden approval
            current_approval_section = main_section.add_section(name="current_approval", title="")
            current_approval_section.add_field(
                Hidden, name="approval-id", default=self.backend_data["approval"]["hash"])

        # this will be filled according to action
        main_section.add_field(
            Hidden, name="target"
        )

        def form_cb(data):
            data["enabled"] = True if data["enabled"] == "1" else False
            if data["enabled"] and data["target"] == "save":
                if data[self.APPROVAL_NEEDED] == self.APPROVAL_NEEDED:
                    data["approval_settings"] = {"status": self.APPROVAL_NEEDED}
                elif data[self.APPROVAL_TIMEOUT] == self.APPROVAL_TIMEOUT:
                    data["approval_settings"] = {"status": self.APPROVAL_TIMEOUT}
                    data["approval_settings"]["delay"] = int(data["approval_delay"])
                elif data[self.APPROVAL_NO] == self.APPROVAL_NO:
                    data["approval_settings"] = {"status": self.APPROVAL_NO}

                if self.contract_valid:
                    data["enabled"] = True
                    data["approval_settings"]["status"] = self.APPROVAL_NO
                    data["approval_settings"].pop("delay", None)

                if self.agreed_collect:
                    data["enabled"] = True

                languages = [k[9:] for k, v in data.iteritems() if v and k.startswith("language_")]
                user_lists = [k[8:] for k, v in data.iteritems() if v and k.startswith("install_")]
                # merge with enabled hidden user lists
                user_lists += [
                    e["name"] for e in self.backend_data["user_lists"]
                    if e["hidden"] and e["enabled"]
                ]

                res = current_state.backend.perform(
                    "updater", "update_settings", {
                        "enabled": True,
                        "approval_settings": data["approval_settings"],
                        "branch": self.branch,
                        "user_lists": user_lists,
                        "languages": languages,
                    }
                )
            elif data["enabled"] and data["target"] in ["grant", "deny"]:
                res = current_state.backend.perform(
                    "updater", "resolve_approval",
                    {"hash": data["approval-id"], "solution": data["target"]}
                )
            else:
                res = current_state.backend.perform(
                    "updater", "update_settings", {
                        "enabled": False,
                    }
                )

            res["target"] = data["target"]
            return "save_result", res

        form.add_callback(form_cb)
        return form
