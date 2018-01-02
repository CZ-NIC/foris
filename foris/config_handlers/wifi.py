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
from foris import validators
from foris.form import Checkbox, Dropdown, Hidden, Password, Radio, Textbox, HorizontalLine
from foris.nuci import client, filters, preprocessors
from foris.nuci.modules.uci_raw import Uci, Config, Section, Option, parse_uci_bool
from foris.state import current_state
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, _

from .base import (
    logger, prepare_guest_configs,
    BaseConfigHandler, DEFAULT_GUEST_NETWORK, DEFAULT_GUEST_PREFIX
)


class WifiHandler(BaseConfigHandler):
    userfriendly_title = gettext("Wi-Fi")

    @staticmethod
    def _get_value(post_data, nuci_data, field, nuci_path, default=None):
        # first try to obtain it from post data then from nuci
        if post_data and field in post_data:
            return post_data[field]
        nuci_res = nuci_data.find_child(nuci_path)
        if nuci_res:
            return nuci_res.value
        return default

    @staticmethod
    def _get_channels(wifi_card):
        channels_2g4 = [("auto", _("auto"))]
        channels_5g = []
        for channel in wifi_card['channels']:
            if channel['disabled']:
                continue
            pretty_channel = "%s (%s MHz%s)" % (
                channel['number'], channel['frequency'], ", DFS" if channel['radar'] else ""
            )
            if channel['frequency'] < 2500:
                channels_2g4.append((str(channel['number']), pretty_channel))
            else:
                channels_5g.append((str(channel['number']), pretty_channel))
        return channels_2g4, channels_5g

    def _add_wifi_section(
            self, wifi_section, wifi_card, radio_to_iface, post_data, nuci_data, last=False):
        HINTS = {
            'password': _(
                "WPA2 pre-shared key, that is required to connect to the "
                "network. Minimum length is 8 characters."
            )
        }

        radio_index = int(wifi_card['name'][3:])
        iface_index = radio_to_iface.get('radio%s' % radio_index)
        if iface_index is None:
            # Interface is not present in the wireless config - skip this radio
            return None

        def prefixed_name(name):
            return "radio%s-%s" % (radio_index, name)

        wifi_main = wifi_section.add_section(
            name=prefixed_name("set_wifi"),
            title=None,
        )

        wifi_main.add_field(
            Hidden, name=prefixed_name("iface_section"),
            nuci_path="uci.wireless.@wifi-iface[%s]" % iface_index,
            nuci_preproc=lambda val: val.name
        )

        # Use numbering starting from one. In rare cases, it may happen that the first radio
        # is not radio0, or that there's a gap between radio numbers, but it should not happen
        # on most of the setups.
        wifi_main.add_field(
            Checkbox, name=prefixed_name("wifi_enabled"),
            label=_("Enable Wi-Fi %s") % (radio_index + 1), default=True,
            nuci_path="uci.wireless.@wifi-iface[%s].disabled" % iface_index,
            nuci_preproc=lambda val: not bool(int(val.value))
        )
        wifi_main.add_field(
            Textbox, name=prefixed_name("ssid"), label=_("SSID"),
            nuci_path="uci.wireless.@wifi-iface[%s].ssid" % iface_index,
            required=True, validators=validators.ByteLenRange(1, 32)
        ).requires(prefixed_name("wifi_enabled"), True)

        wifi_main.add_field(
            Checkbox, name=prefixed_name("ssid_hidden"), label=_("Hide SSID"), default=False,
            nuci_path="uci.wireless.@wifi-iface[%s].hidden" % iface_index,
            hint=_("If set, network is not visible when scanning for available networks.")
        ).requires(prefixed_name("wifi_enabled"), True)

        channels_2g4, channels_5g = self._get_channels(wifi_card)

        is_dual_band = False
        # hwmode choice for dual band devices
        if len(channels_2g4) > 1 and len(channels_5g) > 1:
            is_dual_band = True
            wifi_main.add_field(
                Radio, name=prefixed_name("hwmode"), label=_("Wi-Fi mode"), default="11g",
                args=(("11g", "2.4 GHz (g)"), ("11a", "5 GHz (a)")),
                nuci_path="uci.wireless.radio%s.hwmode" % radio_index,
                nuci_preproc=lambda x: x.value.replace("n", ""),  # old configs used
                # 11ng/11na
                hint=_(
                    "The 2.4 GHz band is more widely supported by clients, but "
                    "tends to have more interference. The 5 GHz band is a newer"
                    " standard and may not be supported by all your devices. It "
                    "usually has less interference, but the signal does not "
                    "carry so well indoors."
                )
            ).requires(prefixed_name("wifi_enabled"), True)

        htmodes = (
            ("NOHT", _("Disabled")),
            ("HT20", _("802.11n - 20 MHz wide channel")),
            ("HT40", _("802.11n - 40 MHz wide channel"))
        )

        # Allow VHT modes only if the card has the capabilities and 5 GHz band is selected
        hwmode = self._get_value(
            post_data, nuci_data,
            "radio%s-hwmode" % radio_index, "uci.wireless.radio%s.hwmode" % radio_index
        )
        allow_vht = wifi_card['vht-capabilities'] and hwmode == "11a"

        if allow_vht:
            htmodes += (
                ("VHT20", _("802.11ac - 20 MHz wide channel")),
                ("VHT40", _("802.11ac - 40 MHz wide channel")),
                ("VHT80", _("802.11ac - 80 MHz wide channel")),
            )

        wifi_main.add_field(
            Dropdown, name=prefixed_name("htmode"), label=_("802.11n/ac mode"),
            args=htmodes,
            nuci_path="uci.wireless.radio%s.htmode" % radio_index,
            hint=_(
                "Change this to adjust 802.11n/ac mode of operation. 802.11n with 40 MHz wide "
                "channels can yield higher throughput but can cause more interference in the "
                "network. If you don't know what to choose, use the default option with 20 MHz "
                "wide channel."
            )
        ).requires(prefixed_name("wifi_enabled"), True)

        # 2.4 GHz channels
        if len(channels_2g4) > 1:
            field_2g4 = wifi_main.add_field(
                Dropdown, name=prefixed_name("channel2g4"), label=_("Network channel"),
                default=channels_2g4[0][0], args=channels_2g4,
                nuci_path="uci.wireless.radio%s.channel" % radio_index
            ).requires(prefixed_name("wifi_enabled"), True)

            if is_dual_band:
                field_2g4.requires(prefixed_name("hwmode"), "11g")

        # 5 GHz channels
        if len(channels_5g) > 1:
            field_5g = wifi_main.add_field(
                Dropdown, name=prefixed_name("channel5g"), label=_("Network channel"),
                default=channels_5g[0][0], args=channels_5g,
                nuci_path="uci.wireless.radio%s.channel" % radio_index
            ).requires(prefixed_name("wifi_enabled"), True)

            if is_dual_band:
                field_5g.requires(prefixed_name("hwmode"), "11a")

        wifi_main.add_field(
            Password, name=prefixed_name("key"), label=_("Network password"),
            nuci_path="uci.wireless.@wifi-iface[%s].key" % iface_index,
            required=True,
            validators=validators.ByteLenRange(8, 63),
            hint=HINTS['password']
        ).requires(prefixed_name("wifi_enabled"), True)

        if current_state.app == "config":
            # Guest wi-fi part
            guest_section = wifi_main.add_section(
                name=prefixed_name("set_guest_wifi"),
                title=_("Guest Wi-Fi"),
                description=_("Set guest Wi-Fi here.")
            )

            guest_section.add_field(
                Checkbox, name=prefixed_name("guest_enabled"),
                label=_("Enable guest Wi-Fi"), default=False,
                nuci_path="uci.wireless.guest_iface_%s.disabled" % iface_index,
                nuci_preproc=lambda value: not parse_uci_bool(value),
                hint=_(
                    "Enables Wi-Fi for guests, which is separated from LAN network. Devices "
                    "connected to this network are allowed to access the internet, but aren't "
                    "allowed to access other devices and the configuration interface of the router. "
                    "Parameters of the guest network can be set in <a href='%(url)s'>the LAN tab</a>. "
                ) % dict(url=reverse("config_page", page_name="lan"))
            ).requires(prefixed_name("wifi_enabled"), True)

            default_ssid = self._get_value(
                post_data, nuci_data,
                prefixed_name("ssid"), "uci.wireless.@wifi-iface[%s].ssid" % iface_index,
                "Turris",
            )
            default_guest_ssid = self._get_value(
                post_data, nuci_data,
                prefixed_name("guest_ssid"), "uci.wireless.guest_iface_%s.ssid" % iface_index,
                "%s-guest" % default_ssid
            )
            guest_section.add_field(
                Textbox, name=prefixed_name("guest_ssid"), label=_("SSID for guests"),
                nuci_path="uci.wireless.guest_iface_%s.ssid" % iface_index,
                required=True, validators=validators.ByteLenRange(1, 32),
                default=default_guest_ssid
            ).requires(prefixed_name("guest_enabled"), True)

            guest_section.add_field(
                Password, name=prefixed_name("guest_key"), label=_("Password for guests"),
                nuci_path="uci.wireless.guest_iface_%s.key" % iface_index,
                required=True,
                default="",
                validators=validators.ByteLenRange(8, 63),
                hint=HINTS['password'],
            ).requires(prefixed_name("guest_enabled"), True)

        # Horizontal line separating wi-fi cards
        if not last:
            wifi_main.add_field(
                HorizontalLine, name=prefixed_name("wifi-separator"), class_="wifi-separator"
            ).requires(prefixed_name("wifi_enabled"), True)

    @staticmethod
    def _get_wireless_cards(stats):
        return stats.data.get('wireless-cards') or None

    def _get_radios(self, cards, wifi_section, radio_to_iface, post_data, nuci_data):
        radios = []
        for idx, card in enumerate(sorted(cards, key=lambda x: x['name'])):
            assert card['name'][0:3] == "phy", "Can not parse card name '%s'" % card['name']
            self._add_wifi_section(
                wifi_section, card, radio_to_iface, post_data, nuci_data, len(cards) - 1 == idx)
            radios.append(card['name'][3:])
        return radios

    @staticmethod
    def _get_radio_to_iface(wifi_form):
        radio_to_iface = {}
        i = 0
        while True:
            radio = wifi_form.nuci_config.find_child("uci.wireless.@wifi-iface[%s].device" % i)
            if not radio:
                break
            # Remember the first interface assigned to the radio
            radio_to_iface.setdefault(radio.value, i)
            i += 1
        return radio_to_iface

    @staticmethod
    def _prepare_radio_cb(data, wireless, radio):
        """ prepares cb for a signle radio part
            :returns: True if guest Wi-Fi is enabled False othewise
            :rtype: bool
        """

        def radio_data(name):
            return data.get("radio%s-%s" % (radio, name))

        iface_section = radio_data('iface_section')
        if not iface_section:
            # There's no section specified for this radio, skip it
            return

        iface = Section(iface_section, "wifi-iface")
        wireless.add(iface)
        device = Section("radio%s" % radio, "wifi-device")
        wireless.add(device)
        if current_state.app == "config":
            guest_iface = Section("guest_iface_%s" % radio, "wifi-iface")
            wireless.add(guest_iface)

        # we must toggle both wifi-ifaces and device
        wifi_enabled = radio_data('wifi_enabled')
        guest_enabled = radio_data("guest_enabled")
        iface.add(Option("disabled", not wifi_enabled))
        device.add(Option("disabled", not wifi_enabled))

        if current_state.app == "config":
            guest_iface.add(Option("disabled", not wifi_enabled or not guest_enabled))

        if wifi_enabled:
            iface.add(Option("ssid", radio_data('ssid')))
            iface.add(Option("hidden", radio_data('ssid_hidden')))
            iface.add(Option("encryption", "psk2+ccmp"))
            iface.add(Option("wpa_group_rekey", "86400"))
            iface.add(Option("key", radio_data('key')))
            if radio_data('channel2g4'):
                channel = radio_data('channel2g4')
            elif radio_data('channel5g'):
                channel = radio_data('channel5g')
            else:
                logger.critical("Saving form without Wi-Fi channel: %s", data)
                channel = "auto"
            hwmode = radio_data('hwmode')
            if hwmode:
                # change hwmode only if we had the choice
                device.add(Option("hwmode", hwmode))
            device.add(Option("htmode", radio_data('htmode')))
            # channel is in wifi-device section
            device.add(Option("channel", channel))

            # setting guest wifi
            if current_state.app == "config":
                if guest_enabled:
                    guest_iface.add(Option("device", "radio%s" % radio))
                    guest_iface.add(Option("mode", "ap"))
                    guest_iface.add(Option("ssid", radio_data('guest_ssid')))
                    guest_iface.add(Option("encryption", "psk2+ccmp"))
                    guest_iface.add(Option("wpa_group_rekey", "86400"))
                    guest_iface.add(Option("key", radio_data('guest_key')))
                    guest_iface.add(Option("disabled", "0"))
                    guest_iface.add(Option("ifname", "guest_turris_%s" % radio))
                    guest_iface.add(Option("network", "guest_turris"))
                    guest_iface.add(Option("isolate", "1"))
                    return True
                else:
                    # disable guest wifi
                    guest_iface.add(Option("disabled", "1"))

        return False

    def get_form(self):
        stats = client.get(filter=filters.stats).find_child("stats")
        cards = self._get_wireless_cards(stats)

        if not cards:
            return None

        wifi_form = fapi.ForisForm(
            "wifi", self.data, filter=filters.wifi_filter())

        # Create mapping of radio_name -> iface_index
        radio_to_iface = self._get_radio_to_iface(wifi_form)

        # Add header section (used for page title)
        wifi_form.add_section(
            name="wifi",
            title=_(self.userfriendly_title),
            description=_(
                "If you want to use your router as a Wi-Fi access point, enable Wi-Fi "
                "here and fill in an SSID (the name of the access point) and a "
                "corresponding password. You can then set up your mobile devices, "
                "using the QR code available next to the form."
            )
        )

        # Add wifi section
        wifi_section = wifi_form.add_section(
            name="wifi_settings",
            title=_("Wi-Fi settings"),
        )

        # Get list of available radios
        radios = self._get_radios(
            cards, wifi_section, radio_to_iface, self.data or {}, wifi_form.nuci_config())

        def wifi_form_cb(data):
            uci = Uci()
            wireless = Config("wireless")
            uci.add(wireless)

            guest_wifi_enabled = False
            for radio in radios:
                if self._prepare_radio_cb(data, wireless, radio):
                    guest_wifi_enabled = True

            guest_interfaces = ["guest_turris_%s" % e for e in sorted(radios)]

            # test whether it is required to pass update guest network
            current_data = client.get(filter=filters.wifi_filter())
            current_enabled = preprocessors.guest_network_enabled(current_data)
            if guest_wifi_enabled and not current_enabled:
                # Guest network handling
                guest_network_subnet = data.get("guest_network_subnet")
                if guest_network_subnet:
                    network, prefix = data.get("guest_network_subnet").split("/")
                else:
                    network, prefix = DEFAULT_GUEST_NETWORK, DEFAULT_GUEST_PREFIX
                prepare_guest_configs(uci, True, network, prefix, guest_interfaces)
            elif guest_wifi_enabled:
                # try to update guest interfaces if the differs
                stored = current_data.find_child("uci.network.guest_turris.ifname")
                if not stored or set(stored.value.split(" ")) != set(guest_interfaces):
                    network_conf = uci.add(Config("network"))
                    interface_section = network_conf.add(Section("guest_turris", "interface"))
                    interface_section.add(Option("ifname", " ".join(guest_interfaces)))

            return "edit_config", uci

        wifi_form.add_callback(wifi_form_cb)

        return wifi_form
