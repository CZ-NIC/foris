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

from bottle import Bottle, request, template
import bottle
from datetime import datetime
import os
from config_handlers import *
from foris import gettext as _
import logging
from nuci import client
from nuci.client import filters
from nuci.exceptions import ConfigRestoreError
from utils import login_required
from collections import OrderedDict
from utils import messages
from utils.bottle_csrf import CSRFPlugin
from utils.routing import reverse


logger = logging.getLogger("admin")


app = Bottle()
app.install(CSRFPlugin())


class ConfigPageMixin(object):
    template = "config/main"

    def call_action(self, action):
        """Call config page action.

        :param action:
        :return: object that can be passed as HTTP response to Bottle
        """
        try:
            return super(ConfigPageMixin, self).call_action(action)
        except NotImplementedError:
            raise bottle.HTTPError(404, "No actions specified for this page.")

    def call_ajax_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        try:
            return super(ConfigPageMixin, self).call_ajax_action(action)
        except NotImplementedError:
            raise bottle.HTTPError(404, "No AJAX actions specified for this page.")

    def default_template(self, **kwargs):
        return template(self.template, **kwargs)

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


class PasswordConfigPage(ConfigPageMixin, PasswordHandler):
    def __init__(self, *args, **kwargs):
        super(PasswordConfigPage, self).__init__(change=True, *args, **kwargs)

    def save(self, *args, **kwargs):
        result = super(PasswordConfigPage, self).save(no_messages=True, *args, **kwargs)
        wrong_old_password = self.form.callback_results.get('wrong_old_password', False)
        if wrong_old_password:
            messages.warning(_("Old password you entered was invalid."))
        elif result:
            messages.success(_("Password was successfully saved."))
        else:
            messages.warning(_("There were some errors in your input."))
        return result


class WanConfigPage(ConfigPageMixin, WanHandler):
    pass


class LanConfigPage(ConfigPageMixin, LanHandler):
    pass


class WifiConfigPage(ConfigPageMixin, WifiHandler):
    template = "config/wifi"


class SystemPasswordConfigPage(ConfigPageMixin, SystemPasswordHandler):
    pass


class MaintenanceConfigPage(ConfigPageMixin, MaintenanceHandler):
    template = "config/maintenance"
    # {{ _("Maintenance") }} - for translation
    userfriendly_title = "Maintenance"

    def _action_config_backup(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        directory = "/tmp/foris_backups"
        filename = "turris-backup-%s.tar.xz" % timestamp
        # TODO: remove old backups, catch errors
        if not os.path.isdir(directory):
            os.mkdir(directory)
        client.save_config_backup(os.path.join(directory, filename))
        return bottle.static_file(filename, directory,
                                  mimetype="application/x-xz", download=True)

    def _action_reboot(self):
        client.reboot()
        bottle.redirect(reverse("config_page", page_name="maintenance"))

    def call_action(self, action):
        if action == "config-backup":
            return self._action_config_backup()
        elif action == "reboot":
            return self._action_reboot()
        raise ValueError("Unknown AJAX action.")

    def save(self, *args, **kwargs):
        result = False
        try:
            result = super(MaintenanceConfigPage, self).save(no_messages=True, *args, **kwargs)
            new_ip = self.form.callback_results.get('new_ip')
            if new_ip:
                messages.success(_("Configuration was successfully restored. After installing "
                                   "the updates and rebooting, router will be available at "
                                   "<a href=\"http://%(new_ip)s\">http://%(new_ip)s</a> in local "
                                   "network.") % dict(new_ip=new_ip))
            else:
                messages.success(_("Configuration was successfully restored."))
                messages.warning(_("IP address of the router could not be determined from the backup."))
        except ConfigRestoreError:
            messages.error(_("Configuration could not be loaded, backup file is probably corrupted."))
            logger.exception("Error when restoring backup.")
        return result


class AboutConfigPage(ConfigPageMixin):
    template = "config/about"
    # {{ _("About") }} - for translation
    userfriendly_title = "About"

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

    def render(self, **kwargs):
        stats = client.get(filter=filters.stats).find_child("stats")
        serial = client.get_serial()
        return self.default_template(stats=stats.data, serial=serial, **kwargs)


class ConfigPageMapItems(OrderedDict):
    def display_names(self):
        return [{'slug': k, 'name': self[k].userfriendly_title} for k in self.keys()]


# names of handlers used in their URL
# use dash-separated names, underscores in URL are ugly
config_page_map = ConfigPageMapItems((
    ('password', PasswordConfigPage),
    ('wan', WanConfigPage),
    ('lan', LanConfigPage),
    ('wifi', WifiConfigPage),
    ('system-password', SystemPasswordConfigPage),
    ('maintenance', MaintenanceConfigPage),
    ('about', AboutConfigPage),
))


def get_config_page(page_name):
    ConfigPage = config_page_map.get(page_name)
    if ConfigPage is None:
        raise bottle.HTTPError(404, "Unknown configuration page.")
    return ConfigPage


@app.route("/", name="config_index")
@login_required
def index():
    return template("config/index", config_pages=config_page_map.display_names())


@app.route("/<page_name:re:.+>/", name="config_page")
@login_required
def config_page_get(page_name):
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    return config_page.render(config_pages=config_page_map.display_names(),
                              active_config_page_key=page_name)


@app.route("/<page_name:re:.+>/", method="POST")
@login_required
def config_page_post(page_name):
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.POST)
    if request.is_xhr:
        # only update is allowed
        logger.debug("ajax request")
        request.POST.pop("update", None)
        return dict(html=config_page.render(is_xhr=True))

    try:
        if config_page.save():
            bottle.redirect(request.fullpath)
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        messages.error(_("Configuration could not be saved due to an internal error."))
        logger.exception("Error when saving form.")
    logger.warning("Form not saved.")
    return config_page.render(config_pages=config_page_map.display_names(),
                              active_handler_key=page_name)


@app.route("/<page_name:re:.+>/action/<action:re:.+>", name="config_action")
@login_required
def config_action(page_name, action):
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    try:
        result = config_page.call_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")


@app.route("/<page_name:re:.+>/ajax")
@login_required
def config_ajax(page_name):
    action = request.GET.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    try:
        result = config_page.call_ajax_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")