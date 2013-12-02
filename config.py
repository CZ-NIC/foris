# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <www.nic.cz>
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
from config_handlers import *
import logging
from utils import login_required
from collections import OrderedDict


logger = logging.getLogger("admin")


app = Bottle()


class ConfigPageMixin(object):
    template = "config/main"

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


@app.route("/<page_name:re:.+>/ajax")
@login_required
def config_ajax(page_name):
    action = request.GET.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    try:
        result = config_page.call_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")