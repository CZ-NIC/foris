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
from foris.state import lazy_cache
from foris.form import Checkbox, Radio, RadioSingle, Number
from foris.nuci import client, filters
from foris.nuci.helpers import contract_valid
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option, List, Value, parse_uci_bool
from foris.nuci.preprocessors import preproc_disabled_to_agreed
from foris.utils.translators import gettext_dummy as gettext, _

from .base import BaseConfigHandler, logger

L10N_SUPPORTED_PATH = '/usr/share/updater/l10n_supported'


class UpdaterAutoUpdatesHandler(BaseConfigHandler):
    """
    Ask whether user agrees with the updater EULA and toggle updater status
    according to that.
    And sets the approval status
    """

    APPROVAL_NO = "no_approvals"
    APPROVAL_TIMEOUT = "timeout"
    APPROVAL_NEEDED = "needed"
    APPROVAL_DEFAULT = APPROVAL_NO

    userfriendly_title = gettext("Updater")

    def get_form(self):

        def approval_preproc_approve_status(nuci_config):
            """Preprocess approval status """
            # try to obtain status from the form data
            if self.data and "approval_status" in self.data:
                return self.data["approval_status"]

            need_item = nuci_config.find_child("uci.updater.approvals.need")
            if not need_item:
                return UpdaterAutoUpdatesHandler.APPROVAL_NO
            if not parse_uci_bool(need_item.value):
                return UpdaterAutoUpdatesHandler.APPROVAL_NO
            seconds_item = nuci_config.find_child("uci.updater.approvals.auto_grant_seconds")
            if not seconds_item:
                return UpdaterAutoUpdatesHandler.APPROVAL_NEEDED

            try:
                hours = int(seconds_item.value)
            except ValueError:
                return UpdaterAutoUpdatesHandler.APPROVAL_NEEDED

            if hours < 0:
                return UpdaterAutoUpdatesHandler.APPROVAL_NEEDED

            return UpdaterAutoUpdatesHandler.APPROVAL_TIMEOUT

        form = fapi.ForisForm("updater_eula", self.data,
                              filter=filters.create_config_filter("updater", "foris"))
        main_section = form.add_section(name="agree_eula",
                                        title=_(self.userfriendly_title))
        main_section.add_field(
            Radio, name="agreed", label=_("I agree"), default="1",
            args=(("1", _("Use automatic updates (recommended)")),
                  ("0", _("Turn automatic updates off"))),
            nuci_preproc=lambda x: "1" if preproc_disabled_to_agreed(x) else "0"
        )
        approval_section = form.add_section(name="approvals", title=_("Update approvals"))
        main_section.add_section(approval_section)
        approval_section.add_field(
            RadioSingle, name=UpdaterAutoUpdatesHandler.APPROVAL_NO, group="approval_status",
            label=_("No approval needed"),
            hint=_("Updates will be performed immediatelly without a user confirmation."),
            nuci_preproc=lambda e: approval_preproc_approve_status(e),
        ).requires("agreed", "1")

        approval_section.add_field(
            RadioSingle, name=UpdaterAutoUpdatesHandler.APPROVAL_TIMEOUT, group="approval_status",
            label=_("Delayed approval"),
            hint=_("Updates will be performed in a while without a user confirmation."),
            nuci_preproc=lambda e: approval_preproc_approve_status(e),
        ).requires("agreed", "1")
        approval_section.add_field(
            Number,
            name="approval_timeout",
            nuci_path="uci.updater.approvals.auto_grant_seconds",
            nuci_preproc=lambda val: int(val.value) / 60 / 60,  # seconds to hours
            validators=[validators.InRange(1, 24 * 7)],
            default=24,
            required=True,
            min=1,
            max=24 * 7,
        ).requires(
            UpdaterAutoUpdatesHandler.APPROVAL_TIMEOUT, UpdaterAutoUpdatesHandler.APPROVAL_TIMEOUT
        ).requires(
            UpdaterAutoUpdatesHandler.APPROVAL_NO, UpdaterAutoUpdatesHandler.APPROVAL_TIMEOUT
        ).requires(
            UpdaterAutoUpdatesHandler.APPROVAL_NEEDED, UpdaterAutoUpdatesHandler.APPROVAL_TIMEOUT
        )

        approval_section.add_field(
            RadioSingle, name=UpdaterAutoUpdatesHandler.APPROVAL_NEEDED, group="approval_status",
            label=_("Approval needed"),
            hint=_("User always needs to confirm the updates."),
            nuci_preproc=lambda e: approval_preproc_approve_status(e),
        ).requires("agreed", "1")

        def form_cb(data):
            agreed = bool(int(data.get("agreed", "0")))
            approval_status = data.get(
                UpdaterAutoUpdatesHandler.APPROVAL_NO, UpdaterAutoUpdatesHandler.APPROVAL_NO)
            auto_grant_seconds = int(data.get("approval_timeout", 24)) * 60 * 60

            uci = Uci()
            updater = uci.add(Config("updater"))
            override = updater.add(Section("override", "override"))
            override.add(Option("disable", not agreed))

            approvals = updater.add_replace(Section("approvals", "approvals"))
            if approval_status == UpdaterAutoUpdatesHandler.APPROVAL_NO:
                approvals.add(Option("need", "0"))
            elif approval_status == UpdaterAutoUpdatesHandler.APPROVAL_NEEDED:
                approvals.add(Option("need", "1"))
            elif approval_status == UpdaterAutoUpdatesHandler.APPROVAL_TIMEOUT:
                approvals.add(Option("need", "1"))
                approvals.add(Option("auto_grant_seconds", auto_grant_seconds))

            return "edit_config", uci

        def save_result_cb(data):
            return "save_result", {'agreed': bool(int(data.get("agreed", "0")))}

        form.add_callback(form_cb)
        form.add_callback(save_result_cb)
        return form


class UpdaterHandler(BaseConfigHandler):
    userfriendly_title = gettext("Updater")

    def __init__(self, *args, **kwargs):
        super(UpdaterHandler, self).__init__(*args, **kwargs)
        lazy_cache.nuci_updater = lambda: client.get(filter=filters.updater).find_child("updater")

    def get_form(self):
        pkg_list = lazy_cache.nuci_updater.pkg_list

        updater_form = fapi.ForisForm(
            "package_lists", self.data, filter=filters.create_config_filter("updater", "foris")
        )
        updater_main = updater_form.add_section(
            name="updater_section",
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

        package_lists_main = updater_main.add_section(
            name="select_package_lists", title=None,
        )

        language_lists_main = updater_main.add_section(
            name="select_languages",
            title=_(
                "If you want to use other language than English you can select it from the "
                "following list:"
            )
        )

        def make_preproc(list_name):
            """Make function for preprocessing value of single pkglist."""
            def preproc(list):
                enabled_names = map(lambda x: x.content, list.children)
                return list_name in enabled_names
            return preproc

        if not contract_valid():
            agreed_collect_opt = updater_form.nuci_config \
                .find_child("uci.foris.eula.agreed_collect")
            agreed_collect = agreed_collect_opt and bool(int(agreed_collect_opt.value))
        else:
            agreed_collect = True

        for pkg_list_item in pkg_list:
            if not contract_valid():
                if pkg_list_item.name == "i_agree_datacollect":
                    # This has special meaning - it's affected by foris.eula.agreed_collect
                    continue
                elif pkg_list_item.name.startswith("i_agree_") and not agreed_collect:
                    # Data collection is not enabled - do not show items prefixed i_agree_
                    continue
            package_lists_main.add_field(
                Checkbox,
                name="install_%s" % pkg_list_item.name,
                label=pkg_list_item.title,
                hint=pkg_list_item.description,
                nuci_path="uci.updater.pkglists.lists",
                nuci_preproc=make_preproc(pkg_list_item.name)
            )

        def make_lang_preproc(lang_name):
            """Make function for preprocessing value of single language."""
            def preproc(lang):
                enabled_langs = map(lambda x: x.content, lang.children) \
                    if lang and lang.children else []
                return lang_name in enabled_langs
            return preproc

        with open(L10N_SUPPORTED_PATH) as f:
            supported_languages = [e.strip() for e in f.readlines()]
        for language in supported_languages:
            language_lists_main.add_field(
                Checkbox,
                name="language_%s" % language,
                label=language,
                nuci_path="uci.updater.l10n.langs",
                nuci_preproc=make_lang_preproc(language),
            )

        def package_lists_form_cb(data):
            uci = Uci()
            updater = Config("updater")
            uci.add(updater)

            pkglists = Section("pkglists", "pkglists")
            updater.add(pkglists)
            new_package_list = List("lists")

            langlists = Section("l10n", "l10n")
            updater.add(langlists)
            new_language_list = List("langs")

            # create List with selected packages
            i = 0
            for k, v in [(k, v) for k, v in data.iteritems() if v and k.startswith("install_")]:
                new_package_list.add(Value(i, k[8:]))
                i += 1
            # If user agreed with data collection, add i_agree_datacollect list
            if agreed_collect:
                new_package_list.add(Value(i, "i_agree_datacollect"))
                i += 1
            if i == 0:
                pkglists.add_removal(new_package_list)
            else:
                pkglists.add_replace(new_package_list)

            # create language list
            i = 0
            for k, v in [(k, v) for k, v in data.iteritems() if v and k.startswith("language_")]:
                new_language_list.add(Value(i, k[9:]))
                i += 1
            if i == 0:
                langlists.add_removal(new_language_list)
            else:
                langlists.add_replace(new_language_list)

            return "edit_config", uci

        def package_lists_run_updater_cb(data):
            logger.info("Checking for updates.")
            client.check_updates()
            return "none", None

        updater_form.add_callback(package_lists_form_cb)
        updater_form.add_callback(package_lists_run_updater_cb)
        return updater_form
