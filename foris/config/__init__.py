# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

from bottle import Bottle, request, template
import bottle

from foris.common import require_contract_valid
from foris.utils.translators import gettext_dummy as gettext, _
from foris.caches import lazy_cache
from foris.config_handlers import (
    backups, collect, dns, misc, notifications, wan, lan, updater, wifi
)
from foris.nuci import client
from foris.nuci.client import filters
from foris.nuci.helpers import make_notification_title, get_wizard_progress
from foris.nuci.preprocessors import preproc_disabled_to_agreed
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
        data = current_state.backend.perform("wan", "get_wan_status")
        if not data["up"]:
            messages.warning(
                _("WAN port has no link, your internet connection probably won't work.")
            )
        return super(WanConfigPage, self).render(**kwargs)

    def _action_check_connection(self):
        return current_state.backend.perform(
            "wan", "connection_test_trigger", {"test_kinds": ["ipv4", "ipv6"]})

    def call_ajax_action(self, action):
        if action == "check-connection":
            return self._action_check_connection()
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
        result, error_message = client.test_notifications()
        if result:
            messages.success(_("Testing message was sent, please check your inbox."))
        else:
            if error_message:
                messages.error(_("Sending of the testing message failed, your configuration is possibly "
                                 "wrong.<br>Error returned:<br><pre>%(error)s</pre>")
                               % dict(error=error_message))
            else:
                messages.error(_("Sending of the testing message failed because of an internal error."))
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

    @require_contract_valid(False)
    def _action_toggle_updater(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="updater"))
        handler = updater.UpdaterAutoUpdatesHandler(request.POST)
        if handler.save():
            messages.success(_("Configuration was successfully saved."))
            bottle.redirect(reverse("config_page", page_name="updater"))
        messages.warning(_("There were some errors in your input."))
        return super(UpdaterConfigPage, self).render(notifications_form=handler.form)

    def _action_process_approval(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="updater"))

        if not request.POST.get("call", None) or not request.POST.get("approval-id", None) or \
                not request.POST["call"] in ["approve", "deny"]:
            messages.error(_("Invalid request arguments."))
            bottle.redirect(reverse("config_page", page_name="updater"))

        if request.POST["call"] == "approve":
            if client.approve_approval(request.POST["approval-id"]):
                messages.success(_("Update was approved."))
                client.check_updates()
            else:
                messages.error(_("Failed to approve the update."))
        elif request.POST["call"] == "deny":
            if client.deny_approval(request.POST["approval-id"]):
                messages.success(_("Update was postponed."))
                client.check_updates()
            else:
                messages.error(_("Failed to postpone the update."))

        bottle.redirect(reverse("config_page", page_name="updater"))

    def call_action(self, action):
        if action == "toggle_updater":
            return self._action_toggle_updater()
        if action == "process_approval":
            return self._action_process_approval()
        raise ValueError("Unknown action.")

    def render(self, **kwargs):
        lazy_cache.nuci_updater = lambda: client.get(
            filter=filters.updater).find_child("updater")
        if not contract_valid():
            auto_updates_handler = updater.UpdaterAutoUpdatesHandler(self.data)
            kwargs['auto_updates_form'] = auto_updates_handler.form
            kwargs['updater_disabled'] = \
                not preproc_disabled_to_agreed(auto_updates_handler.form.nuci_config)
            agreed = current_state.backend.perform("data_collect", "get", {})["agreed"]
            kwargs['collecting_enabled'] = agreed
            current_approvals = [e for e in lazy_cache.nuci_updater.approval_list if e["current"]]
            approval = current_approvals[0] if current_approvals else None

            approval_time = None
            if approval:
                # convert time to some readable form
                approval_time = int(approval["time"])
                approval["time"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(approval_time))

            kwargs['approval'] = approval
            # read approvals status
            show_approvals = auto_updates_handler.form.nuci_config.find_child(
                'uci.updater.approvals.need'
            )
            kwargs['show_approvals'] = show_approvals.value == "1" if show_approvals else False
            auto_grant_seconds = auto_updates_handler.form.nuci_config.find_child(
                'uci.updater.approvals.auto_grant_seconds')
            delayed_approvals = kwargs['show_approvals'] and auto_grant_seconds is not None
            kwargs['delayed_approvals'] = delayed_approvals

            if approval_time:
                kwargs['delayed_approval_time'] = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(approval_time + int(auto_grant_seconds.value))
                ) if auto_grant_seconds else None

        return super(UpdaterConfigPage, self).render(**kwargs)

    def save(self, *args, **kwargs):
        result = super(UpdaterConfigPage, self).save(no_messages=True, *args, **kwargs)
        if result:
            messages.success(_("Configuration was successfully saved. Selected "
                               "packages should be installed or removed shortly."))
        else:
            messages.warning(_("There were some errors in your input."))
        return result


class DataCollectionConfigPage(ConfigPageMixin, collect.UcollectHandler):
    menu_order = 20

    template = "config/data-collection"
    userfriendly_title = gettext("Data collection")

    def render(self, **kwargs):
        status = kwargs.pop("status", None)
        if not contract_valid():
            updater_data = current_state.backend.perform("updater", "get_settings", {})
            kwargs['updater_disabled'] = not updater_data["enabled"]

            if updater_data["enabled"]:
                collect_data = current_state.backend.perform("data_collect", "get", {})
                if collect_data["agreed"]:
                    handler = collect.CollectionToggleHandler(request.POST)
                    kwargs['collection_toggle_form'] = handler.form
                    kwargs['agreed'] = collect_data["agreed"]
                else:
                    handler = collect.RegistrationCheckHandler(request.POST)
                    kwargs['registration_check_form'] = handler.form

        return self.default_template(form=self.form, title=self.userfriendly_title,
                                     description=None, status=status,
                                     **kwargs)

    @require_contract_valid(False)
    def _action_check_registration(self):
        handler = collect.RegistrationCheckHandler(request.POST)
        if not handler.save():
            messages.warning(_("There were some errors in your input."))
            return self.render(registration_check_form=handler.form)

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
                bottle.redirect(reverse("config_page", page_name="data-collection"))
            elif result["status"] == "free":
                messages.info(
                    _('This email address is not registered yet. Please continue to the '
                      '<a href="%(url)s">Turris website</a> and use the registration code '
                      '<strong>%(reg_num)s</strong> to create a new account.')
                    % dict(url=result["url"], reg_num=result["registration_number"]))
                bottle.redirect(reverse("config_page", page_name="data-collection"))
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
        res = [(slug, page) for slug, page in self.items()]
        return sorted(res, key=lambda e: (e[1].menu_order, e[0]))


# names of handlers used in their URL
# use dash-separated names, underscores in URL are ugly
config_page_map = ConfigPageMapItems((
    ('', VirtualConfigPage(gettext("Home page"), 10)),
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
    notifications = client.get_messages()
    return template("config/index", title=_("Home page"),
                    make_notification_title=make_notification_title,
                    active_config_page_key='',
                    notifications=notifications.new)


@login_required
def dismiss_notifications():
    message_ids = request.POST.getall("message_ids[]")
    result = client.dismiss_notifications(message_ids)
    if result:
        return {'success': True, 'displayedIDs': message_ids}
    return {'success': False}


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
    app.route("/notifications/dismiss", method="POST",
              callback=dismiss_notifications)
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
    allowed_step_max, wizard_finished = get_wizard_progress(session)

    if allowed_step_max == 1:
        if session.is_anonymous:
            session.recreate()
        session["user_authenticated"] = True
        session.save()

    if session.get("user_authenticated"):
        login_redirect()

    return dict(
        luci_path="//%(host)s/%(path)s"
        % {'host': bottle.request.get_header('host'), 'path': 'cgi-bin/luci'})
