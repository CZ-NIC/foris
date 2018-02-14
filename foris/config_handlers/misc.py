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

import base64
import bottle

from datetime import datetime

from foris import fapi, validators
from foris.nuci import client, filters
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option
from foris.form import (
    Hidden, Password, Textbox, Dropdown, Checkbox,
)
from foris.state import current_state
from foris.utils import (
    tzinfo, localized_sorted, check_password
)
from foris.utils.translators import gettext_dummy as gettext, _

from .base import BaseConfigHandler


class PasswordHandler(BaseConfigHandler):
    """
    Setting the password
    """

    userfriendly_title = gettext("Password")

    def __init__(self, *args, **kwargs):
        self.change = kwargs.pop("change", False)
        super(PasswordHandler, self).__init__(*args, **kwargs)

    def get_form(self):
        # form definitions
        pw_form = fapi.ForisForm("password", self.data)
        pw_main = pw_form.add_section(name="set_password", title=_(self.userfriendly_title),
                                      description=_("Set your password for this administration "
                                                    "interface. The password must be at least 6 "
                                                    "characters long."))
        if self.change:
            pw_main.add_field(Password, name="old_password", label=_("Current password"))
            label_pass1 = _("New password")
            label_pass2 = _("New password (repeat)")
        else:
            label_pass1 = _("Password")
            label_pass2 = _("Password (repeat)")

        pw_main.add_field(Password, name="password", label=label_pass1, required=True,
                          validators=validators.LenRange(6, 128))
        pw_main.add_field(Password, name="password_validation", label=label_pass2,
                          required=True,
                          validators=validators.EqualTo("password", "password_validation",
                                                        _("Passwords are not equal.")))
        pw_main.add_field(Checkbox, name="set_system_pw",
                          label=_("Use the same password for advanced configuration"),
                          hint=_("Same password would be used for accessing this administration "
                                 "interface, for root user in LuCI web interface and for SSH "
                                 "login. Use a strong password! (If you choose not to set the "
                                 "password for advanced configuration here, you will have the "
                                 "option to do so later. Until then, the root account will be "
                                 "blocked.)"))

        def pw_form_cb(data):
            if self.change:
                if not check_password(data['old_password']):
                    return "save_result", {'wrong_old_password': True}

            encoded_password = base64.b64encode(data["password"])

            current_state.backend.perform(
                "password", "set", {"password": encoded_password, "type": "foris"})

            if data['set_system_pw'] is True:
                current_state.backend.perform(
                    "password", "set", {"password": encoded_password, "type": "system"})

            return "none", None

        pw_form.add_callback(pw_form_cb)

        return pw_form


# TODO depracated will should be removed when we get rid of wizard
class RegionHandler(BaseConfigHandler):
    """
    Setting of the region information - currently only of the timezone.
    """
    userfriendly_title = gettext("Region settings")

    def get_form(self):
        region_form = fapi.ForisForm("region", self.data,
                                     filter=filters.create_config_filter("system"))
        timezone = region_form.add_section(
            name="timezone", title=_(self.userfriendly_title),
            description=_(
                "Please select the timezone the router is being operated in. "
                "Correct setting is required to display the right time and for related functions."
            )
        )

        lang = current_state.language

        def construct_args(items, translation_function=_, key_getter=lambda x: x):
            """
            Helper function that builds args for country/timezone dropdowns.
            If there's only one item, dropdown should contain only that item.
            Otherwise the list of items should be prepended by an empty value.

            :param items: list of filtered TZ data
            :param translation_function: function that returns displayed choice from TZ data
            :param key_getter:
            :return: list of args
            """
            args = localized_sorted(((key_getter(x), translation_function(x)) for x in items),
                                    lang=lang, key=lambda x: x[1])
            if len(args) > 1:
                return [(None, "-" * 16)] + args
            return args

        timezone.add_field(Hidden, name="system_name",
                           nuci_path="uci.system.@system[0]",
                           nuci_preproc=lambda val: val.name)

        regions = localized_sorted(((x, _(x)) for x in tzinfo.regions),
                                   lang=lang, key=lambda x: x[1])
        timezone.add_field(Dropdown, name="region", label=_("Continent or ocean"), required=True,
                           args=regions,
                           nuci_path="uci.system.@system[0].zonename",
                           nuci_preproc=lambda x: x.value.split("/")[0])

        # Get region and offer available countries
        region = region_form.current_data.get('region')
        countries = construct_args(tzinfo.countries_in_region(region),
                                   lambda x: _(tzinfo.countries[x]))
        timezone.add_field(Dropdown, name="country", label=_("Country"), required=True,
                           default=None, args=countries,
                           nuci_path="uci.system.@system[0].zonename",
                           nuci_preproc=lambda x: tzinfo.get_country_for_tz(x.value))\
            .requires("region")

        # Get country and offer available timezones
        country = region_form.current_data.get("country", countries[0][0])

        # It's possible that data contain country from the previous request,
        # in that case fall back to the first item in list of available countries
        if country not in (x[0] for x in countries):
            country = countries[0][0]
        timezones = construct_args(tzinfo.timezones_in_region_and_country(region, country),
                                   translation_function=lambda x: _(x[2]),
                                   key_getter=lambda x: x[0])

        # Offer timezones - but only if a country is selected and is not None (ensured by the
        # requires() method)
        timezone.add_field(Dropdown, name="zonename", label=_("Timezone"), required=True,
                           default=None,
                           args=timezones, nuci_path="uci.system.@system[0].zonename")\
            .requires("country", lambda x: country and x is not None)

        def region_form_cb(data):
            uci = Uci()
            system = Config("system")
            uci.add(system)
            system_section = Section(data['system_name'], "system")
            system.add(system_section)
            zonename = data['zonename']
            system_section.add(Option("zonename", zonename))
            system_section.add(Option("timezone",
                                      tzinfo.get_zoneinfo_for_tz(zonename)))
            return "edit_config", uci

        region_form.add_callback(region_form_cb)
        return region_form


class SystemPasswordHandler(BaseConfigHandler):
    """
    Setting the password of a system user (currently only root's pw).
    """

    userfriendly_title = gettext("Advanced administration")

    def get_form(self):
        system_pw_form = fapi.ForisForm("system_password", self.data)
        system_pw_main = system_pw_form.add_section(
            name="set_password",
            title=_(self.userfriendly_title),
            description=_("In order to access the advanced configuration possibilities which are "
                          "not present here, you must set the root user's password. The advanced "
                          "configuration options can be managed either through the "
                          "<a href=\"//%(host)s/%(path)s\">LuCI web interface</a> "
                          "or over SSH.") % {'host': bottle.request.get_header('host'),
                                             'path': 'cgi-bin/luci'}
        )
        system_pw_main.add_field(Password, name="password", label=_("Password"), required=True,
                                 validators=validators.LenRange(6, 128))
        system_pw_main.add_field(Password, name="password_validation", label=_("Password (repeat)"),
                                 required=True,
                                 validators=validators.EqualTo("password", "password_validation",
                                                               _("Passwords are not equal.")))

        def system_pw_form_cb(data):
            encoded_password = base64.b64encode(data["password"])
            current_state.backend.perform(
                "password", "set", {"password": encoded_password, "type": "system"})
            return "none", None

        system_pw_form.add_callback(system_pw_form_cb)
        return system_pw_form


# TODO depracated will should be removed when we get rid of wizard
class TimeHandler(BaseConfigHandler):
    userfriendly_title = gettext("Time")

    def get_form(self):
        time_form = fapi.ForisForm("time", self.data, filter=filters.time)
        time_main = time_form.add_section(
            name="set_time",
            title=_(self.userfriendly_title),
            description=_("We could not synchronize the time with a timeserver, probably due to a "
                          "loss of connection. It is necessary for the router to have correct time "
                          "in order to function properly. Please, synchronize it with your "
                          "computer's time, or set it manually.")
        )

        time_main.add_field(Textbox, name="time", label=_("Time"), nuci_path="time",
                            nuci_preproc=lambda v: v.local)

        def time_form_cb(data):
            client.set_time(data['time'])
            return "none", None

        time_form.add_callback(time_form_cb)

        return time_form


class UnifiedTimeHandler(BaseConfigHandler):
    """
    Setting of the region information and time
    """
    userfriendly_title = gettext("Region and time")

    def get_form(self):
        data = current_state.backend.perform("time", "get_settings")
        data["zonename"] = "%s/%s" % (data["region"], data["city"])
        data["how_to_set_time"] = data["time_settings"]["how_to_set_time"]
        formatted_date = datetime.strptime(
            data["time_settings"]["time"], "%Y-%m-%dT%H:%M:%S.%f").strftime("%Y-%m-%d %H:%M:%S")
        data["time"] = formatted_date
        data["ntp_time"] = formatted_date

        if self.data:
            # update from post
            data.update(self.data)

            if bottle.request.is_xhr:
                # xhr won't update the settings, so use current time to update it
                data["time"] = formatted_date
                data["ntp_time"] = formatted_date

        region_and_time_form = fapi.ForisForm("region_and_time", data)

        # section just for common description
        main_section = region_and_time_form.add_section(
            name="region_and_time",  title=_(self.userfriendly_title),
            description=_(
                "It is important that your router has the current time properly set. "
                "If our router had an older time set some expired SSL certificates "
                "might have seemed like valid."
            )
        )
        # region section
        region_section = main_section.add_section(
            name="timezone", title=_("Region settings"),
            description=_(
                "Please select the timezone the router is being operated in. "
                "Correct setting is required to display the right time and for related functions."
            )
        )

        lang = current_state.language

        def construct_args(items, translation_function=_, key_getter=lambda x: x):
            """
            Helper function that builds args for country/timezone dropdowns.
            If there's only one item, dropdown should contain only that item.
            Otherwise the list of items should be prepended by an empty value.

            :param items: list of filtered TZ data
            :param translation_function: function that returns displayed choice from TZ data
            :param key_getter:
            :return: list of args
            """
            args = localized_sorted(((key_getter(x), translation_function(x)) for x in items),
                                    lang=lang, key=lambda x: x[1])
            if len(args) > 1:
                return [(None, "-" * 16)] + args
            return args

        regions = localized_sorted(
            ((x, _(x)) for x in tzinfo.regions), lang=lang, key=lambda x: x[1]
        )
        region_section.add_field(
            Dropdown, name="region", label=_("Continent or ocean"), required=True, args=regions
        )

        # Get region and offer available countries
        region = region_and_time_form.current_data.get('region')
        countries = construct_args(
            tzinfo.countries_in_region(region), lambda x: _(tzinfo.countries[x]))
        region_section.add_field(
            Dropdown, name="country", label=_("Country"), required=True,
            default=tzinfo.get_country_for_tz(data["zonename"]), args=countries,
        ).requires("region")

        # Get country and offer available timezones
        country = region_and_time_form.current_data.get("country", countries[0][0])

        # It's possible that data contain country from the previous request,
        # in that case fall back to the first item in list of available countries
        if country not in (x[0] for x in countries):
            country = countries[0][0]
        timezones = construct_args(
            tzinfo.timezones_in_region_and_country(region, country),
            translation_function=lambda x: _(x[2]),
            key_getter=lambda x: x[0]
        )

        # Offer timezones - but only if a country is selected and is not None (ensured by the
        # requires() method)
        region_section.add_field(
            Dropdown, name="zonename", label=_("Timezone"), required=True,
            default=data["zonename"],
            args=timezones
        ).requires("country", lambda x: country and x is not None)

        # time section
        time_section = main_section.add_section(
            name="time", title=_("Time settings"),
            description=_(
                "Time should be up-to-date otherise DNS and other services might not work properly."
            )
        )
        time_section.add_field(
            Dropdown, name="how_to_set_time", label=_("How to set time"),
            description=_("Choose method to store current time into the router."),
            default="ntp",
            args=(
                ("ntp", _("via ntp")),
                ("manual", _("manually")),
            )
        )
        time_section.add_field(
            Textbox, name="time",
            validators=validators.Datetime(),
            label=_("Time"),
            hint=_("Time in YYYY-MM-DD HH:MM:SS format."),
        ).requires("how_to_set_time", "manual")
        time_section.add_field(
            Textbox, name="ntp_time",
            label=_("Time"),
        ).requires("how_to_set_time", "ntp")

        def region_form_cb(data):
            region, city = data["zonename"].split("/")
            msg = {
                "city": city,
                "region": region,
                "timezone": tzinfo.get_zoneinfo_for_tz(data["zonename"]),
                "time_settings": {
                    "how_to_set_time": data["how_to_set_time"],
                }
            }

            if data["how_to_set_time"] == "manual":
                msg["time_settings"]["time"] = datetime.strptime(
                    data["time"], "%Y-%m-%d %H:%M:%S").replace(microsecond=1).isoformat()

            res = current_state.backend.perform("time", "update_settings", msg)
            return "save_result", res  # store {"result": ...} to be used later...

        region_and_time_form.add_callback(region_form_cb)
        return region_and_time_form
