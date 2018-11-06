# coding=utf-8

# Foris
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

import typing
import copy

from datetime import datetime
import base64
import logging
import time

from bottle import Bottle, request, template, response, jinja2_template
from urllib.parse import urlencode
import bottle

from foris.common import login
from foris.guide import Workflow
from foris.utils.translators import gettext_dummy as gettext, _
from foris.config_handlers import (
    backups, dns, misc, notifications, wan, lan, updater, wifi, networks,
    guest, profile
)
from foris.utils import login_required, messages, is_safe_redirect
from foris.middleware.bottle_csrf import CSRFPlugin
from foris.utils.routing import reverse
from foris.state import current_state


logger = logging.getLogger(__name__)


class ConfigPageMixin(object):
    # page url part /config/<slug>
    typing.Optional[str]
    slug = None
    menu_order = 50
    template = "config/main"
    template_type = "simple"

    def call_action(self, action):
        """Call config page action.

        :param action:
        :return: object that can be passed as HTTP response to Bottle
        """
        raise bottle.HTTPError(404, "No actions specified for this page.")

    def call_ajax_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        raise bottle.HTTPError(404, "No AJAX actions specified for this page.")

    def default_template(self, **kwargs):
        if self.template_type == "jinja2":
            page_template = "%s.html.j2" % self.template
            kwargs['template_adapter'] = bottle.Jinja2Template
        else:
            page_template = self.template
        return template(
            page_template, title=_(kwargs.pop('title', self.userfriendly_title)), **kwargs)

    def render(self, **kwargs):
        try:
            form = getattr(self, "form")
            first_section = form.sections[0]
            title = first_section.title
            description = first_section.description
        except (NotImplementedError, AttributeError):
            form = None
            title = self.userfriendly_title
            description = None

        return self.default_template(form=form, title=title, description=description, **kwargs)

    def save(self, *args, **kwargs):
        no_messages = kwargs.pop("no_messages", False)
        result = super(ConfigPageMixin, self).save(*args, **kwargs)
        if no_messages:
            return result
        if result:
            messages.success(_("Configuration was successfully saved."))
        else:
            messages.warning(_("There were some errors in your input."))
        return result

    @staticmethod
    def get_menu_tag_static(cls):
        if current_state.guide.enabled and current_state.guide.current == cls.slug:
            return {
                "show": True,
                "hint": "",
                "text": "<i class='fas fa-reply'></i>",
            }
        else:
            return {
                "show": False,
                "hint": "",
                "text": "",
            }

    @classmethod
    def get_menu_tag(cls):
        return ConfigPageMixin.get_menu_tag_static(cls)

    @staticmethod
    def is_visible_static(cls):
        if current_state.guide.enabled:
            return cls.slug in current_state.guide.steps

        return True

    @classmethod
    def is_visible(cls):
        return ConfigPageMixin.is_visible_static(cls)

    @staticmethod
    def is_enabled_static(cls):
        if current_state.guide.enabled:
            return cls.slug in current_state.guide.available_tabs

        return True

    @classmethod
    def is_enabled(cls):
        return ConfigPageMixin.is_enabled_static(cls)


class NotificationsConfigPage(ConfigPageMixin):
    slug = "notifications"

    menu_order = 10

    template = "config/notifications"
    userfriendly_title = gettext("Notifications")
    template_type = "jinja2"

    def render(self, **kwargs):
        notifications = current_state.backend.perform(
            "router_notifications", "list", {"lang": current_state.language}
        )["notifications"]

        # show only non displayed notifications
        kwargs["notifications"] = [e for e in notifications if not e["displayed"]]

        return super(NotificationsConfigPage, self).render(**kwargs)

    def _action_dismiss_notifications(self):
        notification_ids = request.POST.getall("notification_ids[]")
        response = current_state.backend.perform(
            "router_notifications", "mark_as_displayed", {"ids": notification_ids})
        return response["result"], notification_ids

    def call_ajax_action(self, action):
        if action == "dismiss-notifications":
            bottle.response.set_header("Content-Type", "application/json")
            res = self._action_dismiss_notifications()
            if res[0]:
                return {"success": True, "displayedIDs": res[1]}
            else:
                return {"success": False}

        elif action == "list":
            notifications = current_state.backend.perform(
                "router_notifications", "list", {"lang": current_state.language}
            )["notifications"]
            return template(
                "_notifications.html.j2",
                notifications=[e for e in notifications if not e["displayed"]],
                template_adapter=bottle.Jinja2Template,
            )

        raise ValueError("Unknown AJAX action.")

    @classmethod
    def get_menu_tag(cls):
        return {
            "show": True if current_state.notification_count else False,
            "hint": _("Number of notifications"),
            "text": "%d" % current_state.notification_count,
        }


class PasswordConfigPage(ConfigPageMixin, misc.PasswordHandler):
    slug = "password"
    menu_order = 11
    template = "config/password"
    template_type = "jinja2"

    def __init__(self, *args, **kwargs):
        super(PasswordConfigPage, self).__init__(change=current_state.password_set, *args, **kwargs)

    def save(self, *args, **kwargs):
        result = super(PasswordConfigPage, self).save(no_messages=True, *args, **kwargs)
        wrong_old_password = self.form.callback_results.get('wrong_old_password', False)
        system_password_no_error = self.form.callback_results.get('system_password_no_error', None)
        foris_password_no_error = self.form.callback_results.get('foris_password_no_error', None)
        if wrong_old_password:
            messages.error(_("Old password you entered was not valid."))
            return result

        if system_password_no_error is not None:
            if system_password_no_error:
                messages.success(_("System password was successfully saved."))
            else:
                messages.error(_("Failed to save system password"))
        if foris_password_no_error is not None:
            if foris_password_no_error:
                messages.success(_("Foris password was successfully saved."))
            else:
                messages.error(_("Failed to save Foris password"))

        return result


class ProfileConfigPage(ConfigPageMixin, profile.ProfileHandler):
    slug = "profile"
    menu_order = 12
    template = "config/profile"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs['workflows'] = [
            Workflow(
                e, self.backend_data["current_workflow"] == e,
                self.backend_data["recommended_workflow"] == e
            ) for e in self.backend_data["available_workflows"]
        ]

        # perform some workflow sorting
        SCORE = {
            "router": 1,  # router first
            "bridge": 2,
        }
        kwargs['workflows'].sort(key=lambda e: (SCORE.get(e.name, 99), e.name))
        return super(ProfileConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        result = super(ProfileConfigPage, self).save(no_messages=True, *args, **kwargs)
        if self.form.callback_results["result"]:
            messages.success(_("Guide workflow was sucessfully set."))
        else:
            messages.error(_("Failed to set guide workflow."))
        return result

    @classmethod
    def is_visible(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_enabled_static(cls)


class NetworksConfigPage(ConfigPageMixin, networks.NetworksHandler):
    slug = "networks"
    menu_order = 13
    template = "config/networks"
    template_type = "jinja2"

    def render(self, **kwargs):
        # filter backend data
        filtered = {e: [] for e in self.backend_data["networks"].keys()}
        non_configurable = []
        for network_name, network in self.backend_data["networks"].items():
            for interface in network:
                if interface["configurable"]:
                    filtered[network_name].append(interface)
                else:
                    non_configurable.append(interface)

        # try to show wifis
        kwargs['networks'] = filtered
        for record in sorted(non_configurable, key=lambda x: x["slot"], reverse=True):
            if record["type"] == "wifi":
                lan_record = copy.deepcopy(record)
                lan_record["id"] += "-lan"
                lan_record["slot"] = lan_record["bus"] + "-" + lan_record["slot"]
                filtered["lan"].insert(0, lan_record)

                guest_record = copy.deepcopy(record)
                guest_record["id"] += "-guest"
                guest_record["slot"] = guest_record["bus"] + "-" + guest_record["slot"]
                filtered["guest"].insert(0, guest_record)

        return super(NetworksConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        result = super(NetworksConfigPage, self).save(no_messages=True, *args, **kwargs)
        if self.form.callback_results["result"]:
            messages.success(_("Network configuration was sucessfully updated."))
        else:
            messages.error(_("Unable to update your network configuration."))
        return result

    @classmethod
    def is_enabled(cls):
        if current_state.device in ["turris"]:
            return False
        # Don't show in turrisOS version < "4.0"
        if int(current_state.turris_os_version.split(".", 1)[0]) < 4:
            return False
        return ConfigPageMixin.is_enabled_static(cls)

    @classmethod
    def is_visible(cls):
        return cls.is_enabled()


class WanConfigPage(ConfigPageMixin, wan.WanHandler):
    slug = "wan"
    menu_order = 14

    template = "config/wan"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs['interface_count'] = self.backend_data["interface_count"]
        if not self.status_data["up"]:
            if self.status_data["proto"] == "pppoe":
                messages.warning(_(
                    "You WAN configuration is probably not correct "
                    "or your WAN interface hasn't been properly initialized yet."
                ))
            else:
                messages.warning(
                    _("WAN port has no link, your internet connection probably won't work.")
                )
        return super(WanConfigPage, self).render(**kwargs)

    def _action_check_connection(self, ipv6=True):
        return current_state.backend.perform(
            "wan", "connection_test_trigger", {"test_kinds": ["ipv4", "ipv6"] if ipv6 else ["ipv4"]}
        )

    def call_ajax_action(self, action):
        if action == "check-connection":
            ipv6_type = bottle.request.GET.get("ipv6_type")
            return self._action_check_connection(ipv6_type != "none")
        raise ValueError("Unknown AJAX action.")


class LanConfigPage(ConfigPageMixin, lan.LanHandler):
    slug = "lan"
    menu_order = 15

    template = "config/lan"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs["dhcp_clients"] = self.backend_data["mode_managed"]["dhcp"]["clients"]
        kwargs["interface_count"] = self.backend_data["interface_count"]
        for client in kwargs["dhcp_clients"]:
            client["expires"] = datetime.utcfromtimestamp(client["expires"]).strftime(
                "%Y-%m-%d %H:%M"
            )

        return super(LanConfigPage, self).render(**kwargs)


class GuestConfigPage(ConfigPageMixin, guest.GuestHandler):
    slug = "guest"
    menu_order = 16

    template = "config/guest"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs["dhcp_clients"] = self.backend_data["dhcp"]["clients"]
        kwargs["interface_count"] = self.backend_data["interface_count"]
        for client in kwargs["dhcp_clients"]:
            client["expires"] = datetime.utcfromtimestamp(client["expires"]).strftime(
                "%Y-%m-%d %H:%M"
            )

        return super(GuestConfigPage, self).render(**kwargs)


class TimeConfigPage(ConfigPageMixin, misc.UnifiedTimeHandler):
    """ Timezone / Time configuration """
    slug = "time"
    menu_order = 17

    template = "config/time"
    template_type = "jinja2"

    def render(self, **kwargs):
        kwargs["ntp_servers"] = self.backend_data["time_settings"]["ntp_servers"]
        return super().render(**kwargs)

    def call_ajax_action(self, action):
        if action == "ntpdate-trigger":
            return current_state.backend.perform("time", "ntpdate_trigger")
        raise ValueError("Unknown AJAX action.")


class DNSConfigPage(ConfigPageMixin, dns.DNSHandler):
    slug = "dns"
    menu_order = 18

    template = "config/dns"
    template_type = "jinja2"

    def _action_check_connection(self):
        return current_state.backend.perform(
            "wan", "connection_test_trigger", {"test_kinds": ["dns"]})

    def call_ajax_action(self, action):
        if action == "check-connection":
            return self._action_check_connection()
        raise ValueError("Unknown AJAX action.")


class WifiConfigPage(ConfigPageMixin, wifi.WifiHandler):
    slug = "wifi"
    menu_order = 19

    template = "config/wifi"
    template_type = "jinja2"

    def _action_reset(self):

        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="wifi"))

        data = current_state.backend.perform("wifi", "reset")
        if "result" in data and data["result"] is True:
            messages.success(_("Wi-Fi reset was successful."))
        else:
            messages.error(_("Failed to perform Wi-Fi reset."))

        bottle.redirect(reverse("config_page", page_name="wifi"))

    def call_action(self, action):
        if action == "reset":
            self._action_reset()
        raise ValueError("Unknown action.")

    def save(self, *args, **kwargs):
        super(WifiConfigPage, self).save(no_messages=True, *args, **kwargs)
        return self.form.callback_results.get("result", None)


class MaintenanceConfigPage(ConfigPageMixin, backups.MaintenanceHandler):
    slug = "maintenance"
    menu_order = 20

    template = "config/maintenance"
    template_type = "jinja2"

    userfriendly_title = gettext("Maintenance")

    def _action_config_backup(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = "turris-backup-%s.tar.bz2" % timestamp
        data = current_state.backend.perform("maintain", "generate_backup")
        raw_data = base64.b64decode(data["backup"])

        bottle.response.set_header("Content-Type", "application/x-bz2")
        bottle.response.set_header("Content-Disposition", 'attachment; filename="%s"' % filename)
        bottle.response.set_header("Content-Length", len(raw_data))

        return raw_data

    def _action_save_notifications(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        handler = notifications.NotificationsHandler(request.POST.decode())
        if handler.save():
            messages.success(_("Configuration was successfully saved."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        messages.warning(_("There were some errors in your input."))
        return super(MaintenanceConfigPage, self).render(notifications_form=handler.form)

    def _action_test_notifications(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        data = current_state.backend.perform(
            "router_notifications", "create",
            {
                "msg": "_(This is a testing notification. Please ignore me.)",
                "severity": "news",
                "immediate": True,
            }
        )

        if data["result"]:
            messages.success(_("Testing message was sent, please check your inbox."))
        else:
            messages.error(_(
                "Sending of the testing message failed, your configuration is possibly wrong."
            ))
        bottle.redirect(reverse("config_page", page_name="maintenance"))

    def call_action(self, action):
        if action == "config-backup":
            return self._action_config_backup()
        elif action == "save_notifications":
            return self._action_save_notifications()
        elif action == "test_notifications":
            return self._action_test_notifications()
        raise ValueError("Unknown AJAX action.")

    def render(self, **kwargs):
        notifications_handler = notifications.NotificationsHandler(self.data)
        return super(MaintenanceConfigPage, self).render(
            notifications_form=notifications_handler.form,
            **kwargs
        )

    def save(self, *args, **kwargs):
        super(MaintenanceConfigPage, self).save(no_messages=True, *args, **kwargs)
        result = self.form.callback_results.get('result')
        if result:
            messages.success(_("Configuration was successfully restored. "
                               "Note that a reboot will be required to apply restored "
                               "configuration."))
        else:
            messages.warning(_("Failed to restore the backup from the provided file."))
        return result


class UpdaterConfigPage(ConfigPageMixin, updater.UpdaterHandler):
    slug = "updater"
    menu_order = 21

    template = "config/updater"
    template_type = "jinja2"

    def _action_resolve_approval(self):
        if bottle.request.method != 'POST':
            raise bottle.HTTPError(405, "Method not allowed.")
        try:
            approval_id = bottle.request.POST.get("approval_id")
        except KeyError:
            raise bottle.HTTPError(400, "approval is missing.")

        try:
            solution = bottle.request.POST.get("solution").strip()
        except KeyError:
            raise bottle.HTTPError(400, "solution is missing.")

        if solution not in ("grant", "deny"):
            raise bottle.HTTPError(400, "wrong solution value (expected 'grant' or 'deny').")

        bottle.response.set_header("Content-Type", "application/json")
        return current_state.backend.perform(
            "updater", "resolve_approval", {"hash": approval_id, "solution": solution})

    def call_ajax_action(self, action):
        if action == "resolve_approval":
            return self._action_resolve_approval()
        raise ValueError("Unknown action.")

    def render(self, **kwargs):
        kwargs['branch'] = self.branch
        kwargs['is_updater_enabled'] = lambda: self.updater_enabled
        kwargs['agreed_collect'] = self.agreed_collect
        kwargs['current_approval'] = self.current_approval
        kwargs['get_approval_setting_status'] = lambda: self.approval_setting_status
        kwargs['get_approval_setting_delay'] = lambda: self.approval_setting_delay
        if kwargs['current_approval']['present']:
            kwargs['current_approval']['time'] = datetime.strptime(
                kwargs['current_approval']['time'].split(".", 1)[0], "%Y-%m-%dT%H:%M:%S")

        return super(UpdaterConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        result = super(UpdaterConfigPage, self).save(no_messages=True, *args, **kwargs)

        target = self.form.callback_results.get("target", None)
        if target in ["deny", "grant"]:
            result = self.form.callback_results["result"]
            if result:
                if target == "grant":
                    messages.success(_("Update was approved."))
                elif target == "deny":
                    messages.success(_("Update was postponed."))
            else:
                if target == "grant":
                    messages.error(_("Failed to approve the update."))
                elif target == "deny":
                    messages.error(_("Failed to postpone the update."))
            return result

        if result:
            messages.success(_("Configuration was successfully saved. Selected "
                               "packages should be installed or removed shortly."))
        else:
            messages.warning(_("There were some errors in your input."))
        return result

    @classmethod
    def get_menu_tag(cls):
        if current_state.updater_is_running:
            return {
                "show": current_state.updater_is_running,
                "hint": _("Updater is running"),
                "text": u"<i class='fas fa-sync'></i>",
            }
        else:
            return ConfigPageMixin.get_menu_tag_static(cls)


class GuideFinishedPage(ConfigPageMixin, misc.GuideFinishedHandler):
    slug = "finished"
    menu_order = 90

    template_type = "jinja2"
    template = "config/finished"

    def save(self, *args, **kwargs):
        result = super().save(no_messages=True, *args, **kwargs)
        if not self.form.callback_results["result"]:
            messages.error(_("Failed to finish the guide."))
        return result

    @classmethod
    def is_visible(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if not current_state.guide.enabled:
            return False
        return ConfigPageMixin.is_enabled_static(cls)


class AboutConfigPage(ConfigPageMixin):
    slug = "about"
    menu_order = 99

    template = "config/about"
    template_type = "jinja2"
    userfriendly_title = gettext("About")

    def render(self, **kwargs):
        data = current_state.backend.perform("about", "get")
        # process dates etc
        return self.default_template(data=data, **kwargs)


config_pages = {
    e.slug: e for e in [
        NotificationsConfigPage,
        PasswordConfigPage,
        ProfileConfigPage,
        NetworksConfigPage,
        WanConfigPage,
        TimeConfigPage,
        DNSConfigPage,
        LanConfigPage,
        GuestConfigPage,
        WifiConfigPage,
        MaintenanceConfigPage,
        UpdaterConfigPage,
        GuideFinishedPage,
        AboutConfigPage,
    ]
}


def get_config_pages():
    """ Returns sorted config pages
    """
    res = sorted(config_pages.values(), key=lambda e: (e.menu_order, e.slug))
    return res


def add_config_page(page_class):
    """Register config page in /config/ URL namespace.

    :param page_class: handler class
    """
    if page_class.slug is None:
        raise Exception("Page %s doesn't define a propper slug" % page_class)
    if page_class.slug in config_pages:
        raise Exception("Error when adding page %s slug '%s' is already used in %s" % (
            page_class, page_class.slug, config_pages[page_class.slug]
        ))
    config_pages[page_class.slug] = page_class


def get_config_page(page_name):
    ConfigPage = config_pages.get(page_name, None)
    if ConfigPage is None:
        raise bottle.HTTPError(404, "Unknown configuration page.")
    return ConfigPage


def _redirect_to_default_location():

    next_page = "notifications"
    # by default redirect to current guide step
    if current_state.guide.enabled:
        next_page = current_state.guide.current if current_state.guide.current else next_page

    bottle.redirect(reverse("config_page", page_name=next_page))


@login_required
def index():
    _redirect_to_default_location()


@login_required
def config_page_get(page_name):
    # redirect in case that guide is not passed
    if current_state.guide.enabled and page_name not in current_state.guide.available_tabs:
        bottle.redirect(reverse("config_page", page_name=current_state.guide.current))

    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)

    # test if page is enabled otherwise redirect to default
    if not ConfigPage.is_enabled() or not ConfigPage.is_visible():
        _redirect_to_default_location()

    config_page = ConfigPage()
    return config_page.render(active_config_page_key=page_name)


@login_required
def config_page_post(page_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.POST.decode())
    if request.is_xhr:
        if request.POST.pop("update", None):
            # if update was requested, just render the page - otherwise handle actions as usual
            pass
        else:
            config_page.save()
        return config_page.render(is_xhr=True)
    try:
        if config_page.save():
            bottle.redirect(request.fullpath)
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        messages.error(_("Configuration could not be saved due to an internal error."))
        logger.exception("Error when saving form.")
    logger.warning("Form not saved.")
    return config_page.render(active_config_page_key=page_name)


@login_required
def config_action(page_name, action):
    bottle.SimpleTemplate.defaults['active_config_page'] = page_name
    bottle.Jinja2Template.defaults['active_config_page'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    try:
        result = config_page.call_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")


@login_required
def config_action_post(page_name, action):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.POST.decode())
    if request.is_xhr:
        if request.POST.pop("update", None):
            # if update was requested, just render the page - otherwise handle actions as usual
            return config_page.render(is_xhr=True)
    # check if the button click wasn't any sub-action
    subaction = request.POST.pop("action", None)
    if subaction:
        return config_action_post(page_name, subaction)
    try:
        result = config_page.call_action(action)
        try:
            if not result:
                bottle.redirect(reverse("config_page", page_name=page_name))
        except TypeError:
            # raised by Validator - could happen when the form is posted with wrong fields
            messages.error(_("Configuration could not be saved due to an internal error."))
            logger.exception("Error when saving form.")
        logger.warning("Form not saved.")
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")


@login_required
def config_ajax(page_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    action = request.params.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    try:
        result = config_page.call_ajax_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")


def init_app():
    app = Bottle()
    app.install(CSRFPlugin())
    app.route("/", name="config_index", callback=index)
    app.route("/<page_name:re:.+>/ajax", name="config_ajax", method=("GET", "POST"),
              callback=config_ajax)
    app.route("/<page_name:re:.+>/action/<action:re:.+>", method="POST",
              callback=config_action_post)
    app.route("/<page_name:re:.+>/action/<action:re:.+>", name="config_action",
              callback=config_action)
    app.route("/<page_name:re:.+>/", method="POST",
              callback=config_page_post)
    app.route("/<page_name:re:.+>/", name="config_page",
              callback=config_page_get)
    bottle.SimpleTemplate.defaults['get_config_pages'] = get_config_pages
    bottle.Jinja2Template.defaults['get_config_pages'] = get_config_pages
    return app


def login_redirect():
    next_url = bottle.request.GET.get("next")
    if next_url and is_safe_redirect(next_url, bottle.request.get_header('host')):
        bottle.redirect(next_url)
    bottle.redirect(reverse("config_index"))


@bottle.jinja2_view("index.html.j2")
def top_index():
    session = bottle.request.environ['foris.session']
    if bottle.request.method == 'POST':
        next = bottle.request.POST.get("next", None)
        login(next, session)
        # if login passes it will redirect to a proper page
        # otherwise it contains next parameter
        messages.error(_("The password you entered was not valid."))
        response.status = 403
    else:
        next = bottle.request.GET.get("next", None)
        if not current_state.password_set:  # auto login if no password is set
            if session.is_anonymous:
                session.recreate()
            session["user_authenticated"] = True
            session.save()

        if session.get("user_authenticated"):
            login_redirect()

    return dict(
        luci_path="//%(host)s/%(path)s"
        % {'host': bottle.request.get_header('host'), 'path': 'cgi-bin/luci'},
        next=next
    )
