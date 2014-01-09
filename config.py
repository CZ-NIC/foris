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
import logging
from nuci import client
from nuci.client import filters
from utils import login_required
from collections import OrderedDict
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
        :return: object that can be passes as HTTP response to Bottle
        """
        raise bottle.HTTPError(404, "No actions specified for this page.")

    def call_ajax_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        raise bottle.HTTPError(404, "No AJAX actions specified for this page.")

    def default_template(self, **kwargs):
        return template(self.template, **kwargs)

    def render(self, **kwargs):
        # same premise as in wizard form - we are handling single-section ForisForm
        form = self.form
        first_section = form.sections[0]
        title = first_section.title
        description = first_section.description

        return self.default_template(form=form, title=title, description=description, **kwargs)


class PasswordConfigPage(ConfigPageMixin, PasswordHandler):
    pass


class WanConfigPage(ConfigPageMixin, WanHandler):
    pass


class LanConfigPage(ConfigPageMixin, LanHandler):
    pass


class WifiConfigPage(ConfigPageMixin, WifiHandler):
    template = "config/wifi"


class SystemPasswordConfigPage(ConfigPageMixin, SystemPasswordHandler):
    pass


class MaintenanceConfigPage(ConfigPageMixin):
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

    def render(self, **kwargs):
        return self.default_template(**kwargs)


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
        return self.default_template(stats=stats.data,  **kwargs)


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
        pass
    return config_page.render(active_handler_key=page_name)


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