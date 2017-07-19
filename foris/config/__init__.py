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
import os
import logging
import time
from urlparse import urlunsplit

from bottle import Bottle, request, template
import bottle

from foris.utils.translators import gettext_dummy as gettext, _
from foris.nuci.notifications import make_notification_title
from foris.state import lazy_cache
from foris.config_handlers import backups, collect, dns, misc, wan, lan, updater, wifi
from foris.nuci import client
from foris.nuci.client import filters
from foris.nuci.exceptions import ConfigRestoreError
from foris.nuci.helpers import contract_valid
from foris.nuci.preprocessors import preproc_disabled_to_agreed
from foris.utils import login_required, messages
from foris.middleware.bottle_csrf import CSRFPlugin
from foris.utils.routing import reverse

from .request_decorator import require_contract_valid

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

    def render(self, **kwargs):
        stats = client.get(filter=filters.stats).find_child("stats")
        wan_if = stats.data['interfaces'].get(self.wan_ifname)
        if not (wan_if and wan_if.get('is_up')):
            messages.warning(_("WAN port has no link, your internet connection probably won't work."))
        return super(WanConfigPage, self).render(**kwargs)


class DNSConfigPage(ConfigPageMixin, dns.DNSHandler):
    menu_order = 13

    template = "config/dns"

    def _action_check_connection(self):
        return client.check_connection().check_results

    def call_ajax_action(self, action):
        if action == "check-connection":
            check_results = self._action_check_connection()
            return dict(success=check_results is not None, check_results=check_results)
        raise ValueError("Unknown AJAX action.")


class LanConfigPage(ConfigPageMixin, lan.LanHandler):
    menu_order = 14


class WifiConfigPage(ConfigPageMixin, wifi.WifiHandler):
    menu_order = 15

    template = "config/wifi"


class SystemPasswordConfigPage(ConfigPageMixin, misc.SystemPasswordHandler):
    menu_order = 16


class MaintenanceConfigPage(ConfigPageMixin, backups.MaintenanceHandler):
    menu_order = 17

    template = "config/maintenance"
    userfriendly_title = gettext("Maintenance")

    def _action_config_backup(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        directory = "/tmp/foris_backups"
        filename = "turris-backup-%s.tar.bz2" % timestamp
        # TODO: remove old backups, catch errors
        if not os.path.isdir(directory):
            os.mkdir(directory)
        client.save_config_backup(os.path.join(directory, filename))
        return bottle.static_file(filename, directory,
                                  mimetype="application/x-bz2", download=True)

    def _action_reboot(self):
        client.reboot()
        bottle.redirect(reverse("config_index"))

    def _action_save_notifications(self):
        if bottle.request.method != 'POST':
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="maintenance"))
        handler = misc.NotificationsHandler(request.POST)
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
        elif action == "reboot":
            return self._action_reboot()
        elif action == "save_notifications":
            return self._action_save_notifications()
        elif action == "test_notifications":
            return self._action_test_notifications()
        raise ValueError("Unknown AJAX action.")

    def render(self, **kwargs):
        notifications_handler = misc.NotificationsHandler(self.data)
        return super(MaintenanceConfigPage, self).render(notifications_form=notifications_handler.form,
                                                         **kwargs)

    def save(self, *args, **kwargs):
        result = False
        try:
            result = super(MaintenanceConfigPage, self).save(no_messages=True, *args, **kwargs)
            new_ip = self.form.callback_results.get('new_ip')
            if new_ip:
                # rebuild current URL with new IP
                old_urlparts = bottle.request.urlparts
                new_url = urlunsplit((old_urlparts.scheme, new_ip, old_urlparts.path, "", ""))
                messages.success(_("Configuration was successfully restored. After installing "
                                   "updates and rebooting you can return to this page at "
                                   "<a href=\"%(new_url)s\">%(new_url)s</a> in local "
                                   "network. Please wait a while until router automatically "
                                   "restarts.") % dict(new_url=new_url))
            elif result:
                messages.success(_("Configuration was successfully restored. Please wait a while "
                                   "for installation of updates and automatic restart of the "
                                   "device."))
                messages.warning(_("IP address of the router could not be determined from the backup."))
            else:
                messages.warning(_("There were some errors in your input."))
        except ConfigRestoreError:
            messages.error(_("Configuration could not be loaded, backup file is probably corrupted."))
            logger.exception("Error when restoring backup.")
        return result


class UpdaterConfigPage(ConfigPageMixin, updater.UpdaterHandler):
    menu_order = 18

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
            collecting_opt = auto_updates_handler.form.nuci_config.find_child(
                'uci.foris.eula.agreed_collect')
            kwargs['collecting_enabled'] = collecting_opt and bool(int(collecting_opt.value))
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
    menu_order = 19

    template = "config/data-collection"
    userfriendly_title = gettext("Data collection")

    def render(self, **kwargs):
        status = kwargs.pop("status", None)
        if not contract_valid():
            uci_config = client.get(filter=filters.create_config_filter("foris", "updater"))

            disabled_opt = uci_config.find_child('uci.updater.override.disable')
            updater_disabled = disabled_opt and bool(int(disabled_opt.value))
            kwargs['updater_disabled'] = updater_disabled

            if not updater_disabled:
                agreed_opt = uci_config.find_child('uci.foris.eula.agreed_collect')
                if agreed_opt and bool(int(agreed_opt.value)):
                    handler = collect.CollectionToggleHandler(request.POST)
                    kwargs['collection_toggle_form'] = handler.form
                    kwargs['agreed'] = bool(int(agreed_opt.value))
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

        success = handler.form.callback_results['success']
        response = handler.form.callback_results['response']
        kwargs = {}
        if not success:
            messages.error(_("An error ocurred when checking the registration: "
                             "<br><pre>%(response)s</pre>" % dict(response=response)))
            return self.render()
        else:
            if response.status == "owned":
                messages.success(_("Registration for the entered email is valid. "
                                   "Now you can enable the data collection."))
                collection_toggle_handler = collect.CollectionToggleHandler(request.POST)
                kwargs['collection_toggle_form'] = collection_toggle_handler.form
            elif response.status == "foreign":
                messages.warning(
                    _('This router is currently assigned to a different email address. Please '
                      'continue to the <a href="%(url)s">Turris website</a> and use the '
                      'registration code <strong>%(reg_num)s</strong> for a re-assignment to your '
                      'email address.')
                    % dict(url=response.url, reg_num=response.reg_num))
                bottle.redirect(reverse("config_page", page_name="data-collection"))
            elif response.status == "free":
                messages.info(
                    _('This email address is not registered yet. Please continue to the '
                      '<a href="%(url)s">Turris website</a> and use the registration code '
                      '<strong>%(reg_num)s</strong> to create a new account.')
                    % dict(url=response.url, reg_num=response.reg_num))
                bottle.redirect(reverse("config_page", page_name="data-collection"))
        return self.render(status=response.status,
                           registration_url=response.url,
                           reg_num=response.reg_num, **kwargs)

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
        'connecting': gettext("Connecting"),
        'bad-auth': gettext("Invalid authentication"),
        'broken': gettext("Broken"),
        'unknown': gettext("Unknown status"),
    }

    @require_contract_valid(True)
    def _action_registration_code(self):
        return client.get_registration()

    def call_ajax_action(self, action):
        if action == "registration_code":
            regnum = self._action_registration_code()
            if regnum:
                data = regnum.value
            else:
                data = None
            return dict(success=regnum is not None, data=data)
        raise ValueError("Unknown AJAX action.")

    @staticmethod
    def translate_sending_status(status):
        verbose = _(AboutConfigPage.SENDING_STATUS_TRANSLATION.get(
            status,
            AboutConfigPage.SENDING_STATUS_TRANSLATION['unknown']
        ))
        if status not in AboutConfigPage.SENDING_STATUS_TRANSLATION:
            verbose += " (%s)" % status
        return verbose

    def render(self, **kwargs):
        stats = client.get(filter=filters.stats).find_child("stats")
        serial = client.get_serial()
        if not contract_valid():
            foris_conf = client.get(filter=filters.create_config_filter("foris"))
            agreed_opt = foris_conf.find_child("uci.foris.eula.agreed_collect")
            kwargs['agreed_collect'] = agreed_opt and bool(int(agreed_opt.value))
        return self.default_template(stats=stats.data, serial=serial,
                                     translate_sending_status=self.translate_sending_status,
                                     **kwargs)


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
