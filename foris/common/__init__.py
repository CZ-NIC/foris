# coding=utf-8
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

import bottle
import json
import logging
import os
import re

from functools import wraps

from foris import BASE_DIR
from foris.utils import redirect_unauthenticated, is_safe_redirect, login_required, check_password
from foris.middleware.bottle_csrf import update_csrf_token, CSRFValidationError, CSRFPlugin
from foris.utils.routing import reverse
from foris.utils.translators import translations, set_current_language
from foris.utils.bottle_stuff import clickjacking_protection, clear_lazy_cache, disable_caching
from foris.state import current_state


logger = logging.getLogger("foris.common")


def login(next, session):
    if check_password(bottle.request.POST.get("password")):
        # re-generate session to prevent session fixation
        session.recreate()
        session["user_authenticated"] = True

        update_csrf_token(save_session=False)
        session.save()

        if next and is_safe_redirect(next, bottle.request.get_header("host")):
            bottle.redirect(next)
        else:
            bottle.redirect(reverse("index"))


def logout():
    session = bottle.request.environ["foris.session"]

    if "user_authenticated" in session:
        session.load_anonymous()

    bottle.redirect(reverse("index"))


def foris_403_handler(error):
    if isinstance(error, CSRFValidationError):
        try:
            # maybe the session expired, if so, just redirect the user
            redirect_unauthenticated()
        except bottle.HTTPResponse as e:
            # error handler must return the exception, otherwise it would
            # be raised and not handled by Bottle
            return e

    # otherwise display the standard error page
    bottle.app().default_error_handler(error)


def change_lang(lang):
    """Change language of the interface.

    :param lang: language to set
    :raises: bottle.HTTPError if requested language is not installed
    """
    if lang in translations:
        if set_current_language(lang):
            bottle.request.app.lang = lang
        backlink = bottle.request.GET.get("backlink")
        if backlink and is_safe_redirect(backlink, bottle.request.get_header("host")):
            bottle.redirect(backlink)
        bottle.redirect(reverse("index"))
    else:
        raise bottle.HTTPError(404, "Language '%s' is not available." % lang)


def static(filename):
    """ return static file
    :param filename: url path
    :type filename: str
    :return: http response
    """

    def prepare_response(filename, fs_root):
        response = bottle.static_file(filename, root=fs_root)
        response.add_header("Cache-Control", "public, max-age=31536000")
        return response

    if not bottle.DEBUG:
        logger.warning("Static files should be handled externally in production mode.")

    match = re.match(r"/*plugins/+(\w+)/+(.+)", filename)
    if match:
        plugin_name, plugin_file = match.groups()

        # find correspoding plugin
        for plugin in bottle.app().foris_plugin_loader.plugins:
            if plugin.PLUGIN_NAME == plugin_name:
                return prepare_response(plugin_file, os.path.join(plugin.DIRNAME, "static"))

        return bottle.HTTPError(404, "File does not exist.")

    match = re.match(r"/*generated/+([a-z]{2})/+(.+)", filename)
    if match:
        filename = "/".join(match.groups())
        return prepare_response(
            filename, os.path.join(current_state.assets_path, current_state.app)
        )

    return prepare_response(filename, os.path.join(BASE_DIR, "static"))


@login_required
def reboot():
    data = current_state.backend.perform("maintain", "reboot")

    if bottle.request.is_xhr:
        # return a list of ip addresses where to connect after reboot is performed
        res = bottle.response.copy(cls=bottle.HTTPResponse)
        res.content_type = "application/json"
        res.body = json.dumps(data)
        res.status = 200
        raise res
    else:
        bottle.redirect(reverse("/"))


@login_required
def backend_api():

    data = bottle.request.POST.decode()

    def wrong_format():
        raise bottle.HTTPError(400, "wrong incomming message format")

    controller_id = data.get("controller_id")

    if "action" not in data or "module" not in data or "kind" not in data:
        wrong_format()

    if data["kind"] != "request":
        wrong_format()

    msg_data = data.get("data")
    if msg_data:
        try:
            msg_data = json.loads(msg_data)
        except ValueError:
            wrong_format()

    resp = current_state.backend.perform(
        data["module"], data["action"], msg_data, controller_id=controller_id
    )

    res = bottle.response.copy(cls=bottle.HTTPResponse)
    res.content_type = "application/json"
    res.body = json.dumps(resp)
    res.status = 200
    raise res


@login_required
def leave_guide():
    current_state.backend.perform("web", "update_guide", {"enabled": False})
    bottle.redirect(reverse("/"))


@login_required
def reset_guide():
    current_state.backend.perform("web", "reset_guide")
    bottle.redirect(reverse("/"))


def ping():
    res = bottle.response.copy(cls=bottle.HTTPResponse)
    res.content_type = "application/json"

    next = bottle.request.GET.get("next", None)
    login_url = "%s://%s" % (bottle.request.urlparts.scheme, bottle.request.urlparts.netloc)
    login_url = (
        "%s%s?next=%s" % (login_url, reverse("login"), next)
        if next
        else "%s%s" % (login_url, reverse("login"))
    )
    res.body = json.dumps(dict(msg="pong", loginUrl=login_url))
    res.status = 200
    res.set_header("Access-Control-Allow-Origin", "*")
    res.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    res.set_header("Access-Control-Allow-Headers", "Origin, Accept, Content-Type, X-Requested-With")
    raise res


def init_default_app(index, include_static=False):
    """
    Initialize top-level Foris app - register all routes etc.

    :param include_static: include route to static files
    :type include_static: bool
    :return: instance of Foris Bottle application
    """

    app = bottle.app()
    app.install(CSRFPlugin())
    app.route("/", name="index", callback=index)
    app.route("/", method="POST", name="login", callback=index)
    app.route("/backend-api", method="POST", name="backend-api", callback=backend_api)
    app.route("/lang/<lang:re:\w{2}>", name="change_lang", callback=change_lang)
    app.route("/logout", name="logout", callback=logout)
    app.route("/reboot", name="reboot", callback=reboot)
    app.route("/leave_guide", method="POST", name="leave_guide", callback=leave_guide)
    app.route("/reset_guide", method="POST", name="reset_guide", callback=reset_guide)
    if include_static:
        app.route("/static/<filename:re:.*>", name="static", callback=static)
    # route for testing whether the foris app is alive (used in js)
    app.route("/ping", name="ping", method=("GET", "OPTIONS"), callback=ping)
    return app


def init_common_app(app, prefix):
    """
    Initializes Foris application - use this method to apply properties etc.
    that should be set to main app and all the mounted apps (i.e. to the
    Bottle() instances).


    :param app: instance of bottle application to mount
    :param prefix: prefix which has been used to mount the application
    """
    app.catchall = False  # caught by ReportingMiddleware
    app.error_handler[403] = foris_403_handler
    app.add_hook("after_request", clickjacking_protection)
    app.add_hook("after_request", disable_caching)
    app.add_hook("after_request", clear_lazy_cache)
    app.config["prefix"] = prefix
