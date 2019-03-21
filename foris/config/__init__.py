# Foris
# Copyright (C) 2019 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

import logging

from bottle import Bottle, request, template, response
import bottle

from foris.common import login
from foris.utils.translators import _
from foris.utils import login_required, messages, is_safe_redirect
from foris.middleware.bottle_csrf import CSRFPlugin
from foris.utils.routing import reverse
from foris.state import current_state

from .pages.base import ConfigPageMixin, JoinedPages  # TODO refactor plugins and remove this import

from .pages.notifications import NotificationsConfigPage
from .pages.password import PasswordConfigPage
from .pages.remote import RemoteConfigPage
from .pages.guide import ProfileConfigPage, GuideFinishedPage
from .pages.networks import NetworksConfigPage
from .pages.wan import WanConfigPage
from .pages.time import TimeConfigPage
from .pages.dns import DNSConfigPage
from .pages.lan import LanConfigPage
from .pages.guest import GuestConfigPage
from .pages.wifi import WifiConfigPage
from .pages.maintenance import MaintenanceConfigPage
from .pages.updater import UpdaterConfigPage
from .pages.about import AboutConfigPage


logger = logging.getLogger(__name__)

config_pages = {
    e.slug: e for e in [
        NotificationsConfigPage,
        RemoteConfigPage,
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

    # sort subpages
    for page in res:
        page.subpages.sort(key=lambda e: (e.menu_order, e.slug))
    return res


def add_config_page(page_class):
    """Register config page in /config/ URL namespace.

    :param page_class: handler class
    """
    if page_class.slug is None:
        raise Exception("Page %s doesn't define a propper slug" % page_class)
    page_map = {k: v for k, v in config_pages.items()}

    for page in config_pages.values():
        for subpage in page.subpages:
            page_map[subpage.slug] = subpage

    if page_class.slug in page_map:
        raise Exception("Error when adding page %s slug '%s' is already used in %s" % (
            page_class, page_class.slug, page_map[page_class.slug]
        ))
    config_pages[page_class.slug] = page_class


def get_config_page(page_name):
    ConfigPage = config_pages.get(page_name, None)
    if ConfigPage:
        return ConfigPage

    # Try to iterate through subpages
    for page in config_pages.values():
        for subpage in page.subpages:
            if subpage.slug == page_name:
                return subpage
    raise bottle.HTTPError(404, "Unknown configuration page.")


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
        if request.POST.pop("_update", None):
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
        if request.POST.pop("_update", None):
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


@login_required
def config_ajax_form(page_name, form_name):
    bottle.SimpleTemplate.defaults['active_config_page_key'] = page_name
    bottle.Jinja2Template.defaults['active_config_page_key'] = page_name
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage()
    if not request.is_xhr:
        raise bottle.HTTPError(400, "Should be ajax request")
    try:
        trigger = request.POST.pop("_update", None) is None
        hide = request.POST.pop("_hide", False)

        controller_id = request.POST.pop("_controller_id", None)
        form, response_handler = config_page.get_page_form(
            form_name, request.POST.decode(), controller_id
        )

        message = None
        if form.foris_form.validate() and trigger:
            form.foris_form.save()
            message = response_handler(form.foris_form.callback_results)

        return template(
            form.template_name,
            message=message,
            hide=hide,
            form=form.foris_form,
            ajax_form=form,
            template_adapter=bottle.Jinja2Template,
        )
    except (ValueError, KeyError):
        raise bottle.HTTPError(404, "Form not found.")
    raise bottle.HTTPError(404, "Form not found.")


def config_insecure(page_name, identifier):
    ConfigPage = get_config_page(page_name)
    config_page = ConfigPage(request.GET.decode())
    try:
        return config_page.call_insecure(identifier)
    except ValueError:
        raise bottle.HTTPError(404, "Unknown Insecure link")


def init_app():
    app = Bottle()
    app.install(CSRFPlugin())
    app.route("/", name="config_index", callback=index)
    app.route("/<page_name:re:.+>/ajax", name="config_ajax", method=("GET", "POST"),
              callback=config_ajax)
    app.route("/<page_name:re:.+>/ajax/form/<form_name:re:.+>", name="config_ajax_form", method=("POST"),
              callback=config_ajax_form)
    app.route("/<page_name:re:.+>/action/<action:re:.+>", method="POST",
              callback=config_action_post)
    app.route("/<page_name:re:.+>/action/<action:re:.+>", name="config_action",
              callback=config_action)
    app.route("/<page_name:re:.+>/insecure/<identifier:re:[0-9a-zA-Z-]+>",
              name="config_insecure", callback=config_insecure)
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
