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

from datetime import datetime
import base64
import logging
import time
import urllib

from bottle import Bottle, request, template, response
import bottle

from foris.common import require_contract_valid, login
from foris.utils.translators import gettext_dummy as gettext, _
from foris.config_handlers import (
    backups, collect, dns, misc, notifications, wan, lan, updater, wifi
)
from foris.utils import login_required, messages, is_safe_redirect, contract_valid
from foris.middleware.bottle_csrf import CSRFPlugin
from foris.utils.routing import reverse
from foris.state import current_state


logger = logging.getLogger(__name__)


class ConfigPageMixin(object):
    menu_order = 50
    template = "config/main"

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
        return template(
            self.template, title=_(kwargs.pop('title', self.userfriendly_title)), **kwargs)

    def render(self, **kwargs):
        # same premise as in wizard form - we are handling single-section ForisForm
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
    def menu_tag():
        return {
            "show": False,
            "hint": "",
            "text": "",
        }


class NotificationsConfigPage(ConfigPageMixin):
    menu_order = 10

    template = "config/notifications"
    userfriendly_title = gettext("Notifications")

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
                "_notifications.tpl",
                notifications=[e for e in notifications if not e["displayed"]]
            )

        raise ValueError("Unknown AJAX action.")

    @staticmethod
    def menu_tag():
        return {
            "show": True if current_state.notification_count else False,
            "hint": _("Number of notifications"),
            "text": "%d" % current_state.notification_count,
        }


class PasswordConfigPage(ConfigPageMixin, misc.PasswordHandler):
    menu_order = 11

    def __init__(self, *args, **kwargs):
        super(PasswordConfigPage, self).__init__(change=True, *args, **kwargs)

    def save(self, *args, **kwargs):
        result = super(PasswordConfigPage, self).save(no_messages=True, *args, **kwargs)
        wrong_old_password = self.form.callback_results.get('wrong_old_password', False)
        if wrong_old_password:
            messages.warning(_("Old password you entered was not valid."))
        elif result:
            messages.success(_("Password was successfully saved."))
        else:
            messages.warning(_("There were some errors in your input."))
        return result


class WanConfigPage(ConfigPageMixin, wan.WanHandler):
    menu_order = 12

    template = "config/wan"

    def render(self, **kwargs):
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


class TimeConfigPage(ConfigPageMixin, misc.UnifiedTimeHandler):
    """ Timezone / Time configuration """
    menu_order = 13

    template = "config/time"

    def call_ajax_action(self, action):
        if action == "ntpdate-trigger":
            return current_state.backend.perform("time", "ntpdate_trigger", {})
        raise ValueError("Unknown AJAX action.")


class DNSConfigPage(ConfigPageMixin, dns.DNSHandler):
    menu_order = 14

    template = "config/dns"

    def _action_check_connection(self):
        return current_state.backend.perform(
            "wan", "connection_test_trigger", {"test_kinds": ["dns"]})

    def call_ajax_action(self, action):
        if action == "check-connection":
            return self._action_check_connection()
        raise ValueError("Unknown AJAX action.")


class LanConfigPage(ConfigPageMixin, lan.LanHandler):
    menu_order = 15


class WifiConfigPage(ConfigPageMixin, wifi.WifiHandler):
    menu_order = 16

    template = "config/wifi"

    def _action_reset(self):

        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="wifi"))

        data = current_state.backend.perform("wifi", "reset", {})
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


class SystemPasswordConfigPage(ConfigPageMixin, misc.SystemPasswordHandler):
    menu_order = 17


class MaintenanceConfigPage(ConfigPageMixin, backups.MaintenanceHandler):
    menu_order = 18

    template = "config/maintenance"
    userfriendly_title = gettext("Maintenance")

    def _action_config_backup(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = "turris-backup-%s.tar.bz2" % timestamp
        data = current_state.backend.perform("maintain", "generate_backup", {})
        raw_data = base64.b64decode(data["backup"])

        bottle.response.set_header("Content-Type", "application/x-bz2")
        bottle.response.set_header("Content-Disposition", 'attachment; filename="%s"' % filename)
        bottle.response.set_header("Content-Length", len(raw_data))

        return raw_data

    def _action_save_notifications(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        handler = notifications.NotificationsHandler(request.POST)
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
        return super(MaintenanceConfigPage, self).render(notifications_form=notifications_handler.form,
                                                         **kwargs)

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
    menu_order = 19

    template = "config/updater"

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
        kwargs['contract_valid'] = self.contract_valid
        kwargs['branch'] = self.branch
        kwargs['is_updater_enabled'] = lambda: self.updater_enabled
        kwargs['agreed_collect'] = self.agreed_collect
        kwargs['current_approval'] = self.current_approval
        kwargs['get_approval_setting_status'] = lambda: self.approval_setting_status
        kwargs['get_approval_setting_delay'] = lambda: self.approval_setting_delay
        if kwargs['current_approval']['present']:
            kwargs['current_approval']['time'] = datetime.strptime(
                kwargs['current_approval']['time'], "%Y-%m-%dT%H:%M:%S")

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

    @staticmethod
    def menu_tag():
        return {
            "show": current_state.updater_is_running,
            "hint": _("Updater is running"),
            "text": u"<i class='fas fa-sync'></i>",
        }


class DataCollectionConfigPage(ConfigPageMixin, collect.UcollectHandler):
    menu_order = 20

    template = "config/data-collection"
    userfriendly_title = gettext("Data collection")

    def render(self, **kwargs):
        status = kwargs.pop("status", None)
        if not contract_valid():
            updater_data = current_state.backend.perform("updater", "get_enabled")
            kwargs['updater_disabled'] = not updater_data["enabled"]

            if updater_data["enabled"]:
                collect_data = current_state.backend.perform("data_collect", "get", {})
                if collect_data["agreed"]:
                    handler = collect.CollectionToggleHandler(request.POST)
                    kwargs['collection_toggle_form'] = handler.form
                    kwargs['agreed'] = collect_data["agreed"]
                else:
                    email = request.POST.get("email", request.GET.get("email", ""))
                    handler = collect.RegistrationCheckHandler({"email": email})
                    kwargs['registration_check_form'] = handler.form

        return self.default_template(form=self.form, title=self.userfriendly_title,
                                     description=None, status=status,
                                     **kwargs)

    def save(self, *args, **kwargs):
        super(DataCollectionConfigPage, self).save(no_messages=True, *args, **kwargs)
        result = self.form.callback_results.get('result', False)
        if result:
            messages.success(_("Configuration was successfully saved."))
        else:
            messages.error(_(
                "Failed to update emulated services. Note that you might need to wait till "
                "ucollect is properly installed."
            ))
        return result

    @require_contract_valid(False)
    def _action_check_registration(self):
        handler = collect.RegistrationCheckHandler(request.POST)
        if not handler.save():
            messages.warning(_("There were some errors in your input."))
            return self.render(registration_check_form=handler.form)

        email = handler.data["email"]

        result = handler.form.callback_results
        kwargs = {}
        if not result["success"]:
            messages.error(_("An error ocurred when checking the registration: "
                             "<br><pre>%(error)s</pre>" % dict(error=result["error"])))
            return self.render()
        else:
            if result["status"] == "owned":
                messages.success(_("Registration for the entered email is valid. "
                                   "Now you can enable the data collection."))
                collection_toggle_handler = collect.CollectionToggleHandler(request.POST)
                kwargs['collection_toggle_form'] = collection_toggle_handler.form
            elif result["status"] == "foreign":
                messages.warning(
                    _('This router is currently assigned to a different email address. Please '
                      'continue to the <a href="%(url)s">Turris website</a> and use the '
                      'registration code <strong>%(reg_num)s</strong> for a re-assignment to your '
                      'email address.')
                    % dict(url=result["url"], reg_num=result["registration_number"]))
                bottle.redirect(
                    reverse("config_page", page_name="data-collection") + "?" +
                    urllib.urlencode({"email": email})
                )
            elif result["status"] == "free":
                messages.info(
                    _('This email address is not registered yet. Please continue to the '
                      '<a href="%(url)s">Turris website</a> and use the registration code '
                      '<strong>%(reg_num)s</strong> to create a new account.')
                    % dict(url=result["url"], reg_num=result["registration_number"]))
                bottle.redirect(
                    reverse("config_page", page_name="data-collection") + "?" +
                    urllib.urlencode({"email": email})
                )
            elif result["status"] == "not_found":
                messages.error(
                    _('Router failed to authorize. Please try to validate our email later.'))
                bottle.redirect(
                    reverse("config_page", page_name="data-collection") + "?" +
                    urllib.urlencode({"email": email})
                )
        return self.render(status=result["status"],
                           registration_url=result["url"],
                           reg_num=result["registration_number"], **kwargs)

    @require_contract_valid(False)
    def _action_toggle_collecting(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="data-collection"))

        handler = collect.CollectionToggleHandler(request.POST)
        if handler.save():
            messages.success(_("Configuration was successfully saved."))
            bottle.redirect(reverse("config_page", page_name="data-collection"))

        messages.warning(_("There were some errors in your input."))
        return super(DataCollectionConfigPage, self).render(collection_toggle_form=handler.form)

    def call_action(self, action):
        if action == "check_registration":
            return self._action_check_registration()
        elif action == "toggle_collecting":
            return self._action_toggle_collecting()
        raise ValueError("Unknown action.")


class AboutConfigPage(ConfigPageMixin):
    menu_order = 99

    template = "config/about"
    userfriendly_title = gettext("About")

    SENDING_STATUS_TRANSLATION = {
        'online': gettext("Online"),
        'offline': gettext("Offline"),
        'unknown': gettext("Unknown status"),
    }

    @require_contract_valid(True)
    def _action_registration_code(self):
        data = current_state.backend.perform("about", "get_registration_number", {})
        return data["registration_number"]

    def call_ajax_action(self, action):
        if action == "registration_code":
            regnum = self._action_registration_code()
            return dict(success=regnum is not False, data=regnum)
        raise ValueError("Unknown AJAX action.")

    def render(self, **kwargs):
        data = current_state.backend.perform("about", "get", {})
        data["firewall_status"]["seconds_ago"] = \
            int(time.time() - data["firewall_status"]["last_check"])
        data["firewall_status"]["datetime"] = \
            datetime.fromtimestamp(data["firewall_status"]["last_check"])
        data["firewall_status"]["state_trans"] = \
            self.SENDING_STATUS_TRANSLATION[data["firewall_status"]["state"]]
        data["ucollect_status"]["seconds_ago"] = \
            int(time.time() - data["ucollect_status"]["last_check"])
        data["ucollect_status"]["datetime"] = \
            datetime.fromtimestamp(data["ucollect_status"]["last_check"])
        data["ucollect_status"]["state_trans"] = \
            self.SENDING_STATUS_TRANSLATION[data["ucollect_status"]["state"]]
        # process dates etc
        if not contract_valid():
            agreed = current_state.backend.perform("data_collect", "get", {})["agreed"]
            kwargs['agreed_collect'] = agreed
        return self.default_template(data=data, **kwargs)


class VirtualConfigPage(ConfigPageMixin):
    def __init__(self, title, menu_order):
        self.userfriendly_title = title
        self.menu_order = menu_order


class ConfigPageMapItems(dict):
    def menu_list(self):
        res = [(slug, page, page.menu_tag()) for slug, page in self.items()]
        return sorted(res, key=lambda e: (e[1].menu_order, e[0]))


# names of handlers used in their URL
# use dash-separated names, underscores in URL are ugly
config_page_map = ConfigPageMapItems((
    ('notifications', NotificationsConfigPage),
    ('password', PasswordConfigPage),
    ('wan', WanConfigPage),
    ('time', TimeConfigPage),
    ('dns', DNSConfigPage),
    ('lan', LanConfigPage),
    ('wifi', WifiConfigPage),
    ('system-password', SystemPasswordConfigPage),
    ('maintenance', MaintenanceConfigPage),
    ('updater', UpdaterConfigPage),
    ('data-collection', DataCollectionConfigPage),
    ('about', AboutConfigPage),
))

# config pages that are not shown in the menu
extra_config_pages = ConfigPageMapItems()


def add_config_page(page_name, page_class, top_level=False):
    """Register config page in /config/ URL namespace.

    :param page_name: config page name (shown in url)
    :param page_class: handler class
    :param top_level: add to top-level navigation
    """
    if top_level:
        config_page_map[page_name] = page_class
    else:
        extra_config_pages[page_name] = page_class


def get_config_page(page_name):
    ConfigPage = config_page_map.get(page_name,
                                     extra_config_pages.get(page_name))
    if ConfigPage is None:
        raise bottle.HTTPError(404, "Unknown configuration page.")
    return ConfigPage


@login_required
def index():
    bottle.redirect(reverse("config_page", page_name="notifications"))


@login_required
def config_page_get(page_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    return config_page.render(active_config_page_key=page_name)


@login_required
def config_page_post(page_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.POST)
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
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.POST)
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
    bottle.SimpleTemplate.defaults['config_pages'] = config_page_map
    return app


def login_redirect():
    next_url = bottle.request.GET.get("next")
    if next_url and is_safe_redirect(next_url, bottle.request.get_header('host')):
        bottle.redirect(next_url)
    bottle.redirect(reverse("config_index"))


@bottle.view("index")
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
