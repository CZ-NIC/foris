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

import typing

from foris import fapi
from foris import validators
from foris.form import Checkbox, Dropdown, PasswordWithHide, Radio, Textbox, HorizontalLine
from foris.state import current_state
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, _

from .base import BaseConfigHandler


class WifiHandler(BaseConfigHandler):
    userfriendly_title = gettext("Wi-Fi")

    def get_form(self):
        ajax_form = WifiEditForm(self.data)

        return ajax_form.foris_form


class WifiEditForm(fapi.ForisAjaxForm):
    template_name = "config/_wifi_edit.html.j2"

    def __init__(self, data, controller_id=None, enable_guest=True):
        self.enable_guest = enable_guest
        super().__init__(data, controller_id)
        self.title = _("Configure WiFi for '%s'") % controller_id

    @staticmethod
    def prefixed(index, name):
        return "radio%d-%s" % (index, name)

    def convert_data_from_backend_to_form(self, backend_data: dict) -> dict:
        form_data = {}
        for device in backend_data["devices"]:

            def prefixed(name):
                return WifiEditForm.prefixed(device["id"], name)

            form_data[prefixed("device_enabled")] = device["enabled"]
            form_data[prefixed("ssid")] = device["SSID"]
            form_data[prefixed("ssid_hidden")] = device["hidden"]
            form_data[prefixed("hwmode")] = device["hwmode"]
            form_data[prefixed("htmode")] = device["htmode"]
            form_data[prefixed("channel")] = str(device["channel"])
            form_data[prefixed("password")] = device["password"]
            form_data[prefixed("guest_enabled")] = device["guest_wifi"]["enabled"]
            form_data[prefixed("guest_ssid")] = device["guest_wifi"]["SSID"]
            form_data[prefixed("guest_password")] = device["guest_wifi"]["password"]

        return form_data

    def convert_data_from_form_to_backend(
        self, form_data: dict, device_ids: typing.List[str]
    ) -> dict:

        res = []

        for dev_id in device_ids:

            def prefixed(name):
                return WifiEditForm.prefixed(dev_id, name)

            dev_rec = {"id": dev_id}
            dev_rec["enabled"] = form_data[prefixed("device_enabled")]
            if dev_rec["enabled"]:
                dev_rec["SSID"] = form_data[prefixed("ssid")]
                dev_rec["hidden"] = form_data[prefixed("ssid_hidden")]
                dev_rec["hwmode"] = form_data[prefixed("hwmode")]
                dev_rec["htmode"] = form_data[prefixed("htmode")]
                dev_rec["channel"] = int(form_data[prefixed("channel")])
                dev_rec["guest_wifi"] = {}
                dev_rec["guest_wifi"]["enabled"] = form_data.get(prefixed("guest_enabled"), False)
                dev_rec["password"] = form_data[prefixed("password")]
                if dev_rec["guest_wifi"]["enabled"]:
                    dev_rec["guest_wifi"]["SSID"] = form_data[prefixed("guest_ssid")]
                    dev_rec["guest_wifi"]["password"] = form_data[prefixed("guest_password")]

            res.append(dev_rec)

        return {"devices": res}

    def make_form(self, data: typing.Optional[dict]) -> fapi.ForisForm:

        backend_data = current_state.backend.perform(
            "wifi", "get_settings", controller_id=self.controller_id
        )
        form_data = self.convert_data_from_backend_to_form(backend_data)
        if data:
            form_data.update(data)

        used_bands = []
        for field_name, band in [(k, v) for k, v in form_data.items() if k.endswith("hwmode")]:
            # radioX-hwmode => X
            radio_number = field_name.split("-", 1)[0][len("radio"):]
            radio_enabled = form_data.get(f"radio{radio_number}-device_enabled", False)
            if (isinstance(radio_enabled, bool) and radio_enabled) or radio_enabled == "1":
                used_bands.append(band)

        wifi_form = fapi.ForisForm("wifi", form_data)

        # display conflict message when two wifis are using the same band
        wifi_form.band_conflict = not (len(used_bands) == len(set(used_bands)))

        wifi_form.add_section(
            name="wifi",
            title=_("Wi-Fi"),
            description=_(
                "If you want to use your router as a Wi-Fi access point, enable Wi-Fi "
                "here and fill in an SSID (the name of the access point) and a "
                "corresponding password. You can then set up your mobile devices, "
                "using the QR code available within the form."
            ),
        )

        # Add wifi section
        wifi_section = wifi_form.add_section(name="wifi_settings", title=_("Wi-Fi settings"))

        for idx, device in enumerate(backend_data["devices"]):
            prefix = WifiEditForm.prefixed(device["id"], "")
            device_form_data = {
                k[len(prefix) :]: v for k, v in form_data.items() if k.startswith(prefix)
            }  # prefix removed
            self._prepare_device_fields(
                wifi_section, device, device_form_data, len(backend_data["devices"]) - 1 == idx
            )

        def form_cb(data):
            update_data = self.convert_data_from_form_to_backend(
                data, [e["id"] for e in backend_data["devices"]]
            )
            res = current_state.backend.perform(
                "wifi", "update_settings", update_data, controller_id=self.controller_id
            )
            return "save_result", res

        wifi_form.add_callback(form_cb)
        return wifi_form

    def _prepare_device_fields(self, section, device, form_data, last=False):
        HINTS = {
            "password": _(
                "WPA2 pre-shared key, that is required to connect to the "
                "network. Minimum length is 8 characters."
            )
        }

        def prefixed(name):
            return WifiEditForm.prefixed(device["id"], name)

        # get corresponding band
        bands = [e for e in device["available_bands"] if e["hwmode"] == form_data["hwmode"]]
        if not bands:
            # wrong hwmode selected pick the first one from available
            band = device["available_bands"][0]
            form_data["hwmode"] = device["available_bands"][0]["hwmode"]
        else:
            band = bands[0]

        wifi_main = section.add_section(name=prefixed("set_wifi"), title=None)
        wifi_main.add_field(
            Checkbox,
            name=prefixed("device_enabled"),
            label=_("Enable Wi-Fi %s") % (device["id"] + 1),
            default=True,
        )
        wifi_main.add_field(
            Textbox,
            name=prefixed("ssid"),
            label=_("SSID"),
            required=True,
            validators=validators.ByteLenRange(1, 32),
        ).requires(prefixed("device_enabled"), True)
        wifi_main.add_field(
            Checkbox,
            name=prefixed("ssid_hidden"),
            label=_("Hide SSID"),
            default=False,
            hint=_("If set, network is not visible when scanning for available networks."),
        ).requires(prefixed("device_enabled"), True)

        wifi_main.add_field(
            Radio,
            name=prefixed("hwmode"),
            label=_("Wi-Fi mode"),
            args=[
                e
                for e in (("11g", "2.4 GHz (g)"), ("11a", "5 GHz (a)"))
                if e[0] in [b["hwmode"] for b in device["available_bands"]]
            ],
            hint=_(
                "The 2.4 GHz band is more widely supported by clients, but "
                "tends to have more interference. The 5 GHz band is a newer"
                " standard and may not be supported by all your devices. It "
                "usually has less interference, but the signal does not "
                "carry so well indoors."
            ),
        ).requires(prefixed("device_enabled"), True)

        htmodes = (
            ("NOHT", _("Disabled")),
            ("HT20", _("802.11n - 20 MHz wide channel")),
            ("HT40", _("802.11n - 40 MHz wide channel")),
            ("VHT20", _("802.11ac - 20 MHz wide channel")),
            ("VHT40", _("802.11ac - 40 MHz wide channel")),
            ("VHT80", _("802.11ac - 80 MHz wide channel")),
            ("VHT160", _("802.11ac - 160 MHz wide channel")),
        )
        wifi_main.add_field(
            Dropdown,
            name=prefixed("htmode"),
            label=_("802.11n/ac mode"),
            args=[e for e in htmodes if e[0] in band["available_htmodes"]],
            hint=_(
                "Change this to adjust 802.11n/ac mode of operation. 802.11n with 40 MHz wide "
                "channels can yield higher throughput but can cause more interference in the "
                "network. If you don't know what to choose, use the default option with 20 MHz "
                "wide channel."
            ),
        ).requires(prefixed("device_enabled"), True).requires(
            prefixed("hwmode"), lambda val: val in ("11g", "11a")
        )  # this req is added to rerender htmodes when hwmode changes

        channels = [("0", _("auto"))] + [
            (
                str(e["number"]),
                ("%d (%d MHz%s)" % (e["number"], e["frequency"], ", DFS" if e["radar"] else "")),
            )
            for e in band["available_channels"]
        ]
        wifi_main.add_field(
            Dropdown,
            name=prefixed("channel"),
            label=_("Network channel"),
            default="0",
            args=channels,
        ).requires(prefixed("device_enabled"), True).requires(
            prefixed("hwmode"), lambda val: val in ("11g", "11a")
        )  # this req is added to rerender channel list when hwmode changes

        wifi_main.add_field(
            PasswordWithHide,
            name=prefixed("password"),
            label=_("Network password"),
            required=True,
            validators=validators.ByteLenRange(8, 63),
            hint=HINTS["password"],
        ).requires(prefixed("device_enabled"), True)

        if current_state.app == "config" and self.enable_guest:
            # Guest wi-fi part
            guest_section = wifi_main.add_section(
                name=prefixed("set_guest_wifi"),
                title=_("Guest Wi-Fi"),
                description=_("Set guest Wi-Fi here."),
            )
            guest_section.add_field(
                Checkbox,
                name=prefixed("guest_enabled"),
                label=_("Enable guest Wi-Fi"),
                default=False,
                hint=_(
                    "Enables Wi-Fi for guests, which is separated from LAN network. Devices "
                    "connected to this network are allowed to access the internet, but aren't "
                    "allowed to access other devices and the configuration interface of the "
                    "router. Parameters of the guest network can be set in <a href='%(url)s'>the "
                    "Guest network tab</a>."
                )
                % dict(url=reverse("config_page", page_name="guest")),
            ).requires(prefixed("device_enabled"), True)
            guest_section.add_field(
                Textbox,
                name=prefixed("guest_ssid"),
                label=_("SSID for guests"),
                required=True,
                validators=validators.ByteLenRange(1, 32),
            ).requires(prefixed("guest_enabled"), True)
            guest_section.add_field(
                PasswordWithHide,
                name=prefixed("guest_password"),
                label=_("Password for guests"),
                required=True,
                default="",
                validators=validators.ByteLenRange(8, 63),
                hint=HINTS["password"],
            ).requires(prefixed("guest_enabled"), True)

        # Horizontal line separating wi-fi cards
        if not last:
            wifi_main.add_field(
                HorizontalLine, name=prefixed("wifi-separator"), class_="wifi-separator"
            ).requires(prefixed("device_enabled"), True)
