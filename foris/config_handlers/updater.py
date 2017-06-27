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
from foris.core import gettext_dummy as gettext, ugettext as _
from foris.form import Checkbox, Radio
from foris.nuci import client, filters
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option, List, Value
from foris.nuci.preprocessors import preproc_disabled_to_agreed
from foris.utils import contract_valid

from .base import BaseConfigHandler, logger

L10N_SUPPORTED_PATH = '/usr/share/updater/l10n_supported'

class UpdaterEulaHandler(BaseConfigHandler):
    """
    Ask whether user agrees with the updater EULA and toggle updater status
    according to that.
    """

    userfriendly_title = gettext("Updater")

    def get_form(self):
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

        def form_cb(data):
            agreed = bool(int(data.get("agreed", "0")))

            uci = Uci()
            updater = uci.add(Config("updater"))
            override = updater.add(Section("override", "override"))
            override.add(Option("disable", not agreed))

            return "edit_config", uci

        def save_result_cb(data):
            return "save_result", {'agreed': bool(int(data.get("agreed", "0")))}

        form.add_callback(form_cb)
        form.add_callback(save_result_cb)
        return form


class UpdaterHandler(BaseConfigHandler):
    userfriendly_title = gettext("Updater")

    def get_form(self):
        pkg_list = client.get(filter=filters.updater).find_child("updater").pkg_list

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
