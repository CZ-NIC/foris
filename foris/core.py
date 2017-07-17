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

# builtins
import logging
import os

import config as config_app
import wizard as wizard_app

# 3rd party
import bottle
from bottle_i18n import I18NMiddleware, I18NPlugin, i18n_defaults

# local
from . import __version__ as foris_version
from .common import (
    index, login, foris_403_handler, render_js_md5, render_js, logout, change_lang, static
)
from .middleware.sessions import SessionMiddleware
from .middleware.reporting import ReportingMiddleware
from .nuci import client
from .nuci.helpers import contract_valid, read_uci_lang
from .langs import iso2to3, translation_names, DEFAULT_LANGUAGE
from .plugins import ForisPluginLoader
from .utils import (
    is_user_authenticated, template_helpers
)
from .utils.bottle_csrf import get_csrf_token, CSRFPlugin
from .utils import DEVICE_CUSTOMIZATION, messages
from .utils.routing import reverse, static as static_path
from .utils.translators import translations, ugettext, ungettext

from .state import lazy_cache


logger = logging.getLogger("foris")

BASE_DIR = os.path.dirname(__file__)


# internationalization
i18n_defaults(bottle.SimpleTemplate, bottle.request)

bottle.SimpleTemplate.defaults['trans'] = lambda msgid: ugettext(msgid)  # workaround
bottle.SimpleTemplate.defaults['translation_names'] = translation_names
bottle.SimpleTemplate.defaults['translations'] = [e for e in translations]
bottle.SimpleTemplate.defaults['iso2to3'] = iso2to3
bottle.SimpleTemplate.defaults['ungettext'] = lambda singular, plural, n: ungettext(singular, plural, n)
bottle.SimpleTemplate.defaults['DEVICE_CUSTOMIZATION'] = DEVICE_CUSTOMIZATION
bottle.SimpleTemplate.defaults['contract_valid'] = contract_valid
bottle.SimpleTemplate.defaults['foris_version'] = foris_version

# template defaults
# this is not really straight-forward, check for user_authenticated() (with brackets) in template,
# because bool(user_authenticated) is always True - it means bool(<function ...>)
bottle.SimpleTemplate.defaults["user_authenticated"] =\
    lambda: bottle.request.environ["foris.session"].get("user_authenticated")
bottle.SimpleTemplate.defaults["request"] = bottle.request
bottle.SimpleTemplate.defaults["url"] = lambda name, **kwargs: reverse(name, **kwargs)
bottle.SimpleTemplate.defaults["static"] = static_path
bottle.SimpleTemplate.defaults["get_csrf_token"] = get_csrf_token
bottle.SimpleTemplate.defaults["helpers"] = template_helpers
bottle.SimpleTemplate.defaults['js_md5'] = lambda filename: render_js_md5(filename)

# messages
messages.set_template_defaults(bottle.SimpleTemplate)


def route_list(app, prefix1="", prefix2=""):
    res = []
    for route in app.routes:
        path1 = prefix1 + route.rule
        path2 = prefix2
        for name, filter, token in app.router._itertokens(route.rule):
            if not filter:
                # simple token
                path2 += name
            elif filter == 're':
                # insert regexp
                path2 += token

        if route.method == 'PROXY':
            res += route_list(route.config['mountpoint.target'], prefix1=path1, prefix2=path2)
        else:
            res.append((route.method, path1, path2))
    return res


def route_list_debug(app):
    res = []
    for method, bottle_path, regex_path in route_list(app):
        res.append("%s %s" % (method, bottle_path))
    return res


def route_list_cmdline(app):
    res = []
    for method, bottle_path, regex_path in route_list(app):
        res.append(regex_path)
    return res


def clickjacking_protection():
    # we don't use frames at all, we can safely deny opening pages in frames
    bottle.response.headers['X-Frame-Options'] = 'DENY'


def disable_caching(authenticated_only=True):
    """
    Hook for disabling caching.

    :param authenticated_only: apply only if user is authenticated
    """
    if not authenticated_only or authenticated_only and is_user_authenticated():
        bottle.response.headers['Cache-Control'] = "no-store, no-cache, must-revalidate, " \
                                                   "no-transform, max-age=0, post-check=0, pre-check=0"
        bottle.response.headers['Pragma'] = "no-cache"


def clear_lazy_cache():
    lazy_cache.clear()


def init_foris_app(app, prefix):
    """
    Initializes Foris application - use this method to apply properties etc.
    that should be set to main app and all the mounted apps (i.e. to the
    Bottle() instances).


    :param app: instance of bottle application to mount
    :param prefix: prefix which has been used to mount the application
    """
    app.catchall = False  # caught by ReportingMiddleware
    app.error_handler[403] = foris_403_handler
    app.add_hook('after_request', clickjacking_protection)
    app.add_hook('after_request', disable_caching)
    app.add_hook('after_request', clear_lazy_cache)
    app.config['prefix'] = prefix


def get_arg_parser():
    """
    Create ArgumentParser instance with Foris arguments.

    :return: instance of ArgumentParser
    """
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_argument_group("run server")
    group.add_argument("-H", "--host", default="0.0.0.0")
    group.add_argument("-p", "--port", type=int, default=8080)
    group.add_argument("--session-timeout", type=int, default=900,
                       help="session timeout (in seconds)")
    group.add_argument("-s", "--server", choices=["wsgiref", "flup", "cgi"], default="wsgiref")
    group.add_argument("-d", "--debug", action="store_true")
    group.add_argument("--noauth", action="store_true",
                       help="disable authentication (available only in debug mode)")
    group.add_argument("--nucipath", help="path to Nuci binary")
    parser.add_argument("-R", "--routes", action="store_true", help="print routes and exit")
    group.add_argument(
        "-S", "--static", action="store_true",
        help="serve static files directly through foris app (should be used for debug only)"
    )
    return parser


def init_default_app(include_static=False):
    """
    Initialize top-level Foris app - register all routes etc.

    :param include_static: include route to static files
    :type include_static: bool
    :return: instance of Foris Bottle application
    """

    app = bottle.app()
    app.install(CSRFPlugin())
    app.route("/", name="index", callback=index)
    app.route("/lang/<lang:re:\w{2}>", name="change_lang", callback=change_lang)
    app.route("/", method="POST", name="login", callback=login)
    app.route("/logout", name="logout", callback=logout)
    if include_static:
        app.route('/static/<filename:re:.*>', name="static", callback=static)
    app.route("/js/<filename:re:.*>", name="render_js", callback=render_js)
    return app


def prepare_main_app(args):
    """
    Prepare Foris main application - i.e. apply CLI arguments, mount applications,
    install hooks and middleware etc...

    :param args: arguments received from ArgumentParser.parse_args().
    :return: bottle.app() for Foris
    """
    app = init_default_app(args.static)

    # basic and bottle settings
    template_dir = os.path.join(BASE_DIR, "templates")
    bottle.TEMPLATE_PATH.append(template_dir)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    # mount apps
    app.mount("/config", config_app.init_app())
    app.mount("/wizard", wizard_app.init_app())

    if args.debug:
        if args.noauth:
            logger.warning("authentication disabled")
            app.config["no_auth"] = True

    # set custom app attributes for main app and all mounted apps
    init_foris_app(app, None)
    for route in app.routes:
        if route.config.get("mountpoint"):
            mounted = route.config['mountpoint.target']
            prefix = route.config['mountpoint.prefix']
            init_foris_app(mounted, prefix)

    if args.nucipath:
        client.StaticNetconfConnection.set_bin_path(args.nucipath)

    # load Foris plugins before applying Bottle plugins to app
    loader = ForisPluginLoader(app)
    loader.autoload_plugins()

    # print routes to console and exit
    if args.routes:
        routes = route_list_cmdline(app)
        print("\n".join(sorted(set(routes))))
        return app

    # print routes in debug mode
    if args.debug:
        routes = route_list_debug(app)
        logger.debug("Routes:\n%s", "\n".join(routes))

    # read language saved in Uci
    lang = read_uci_lang(DEFAULT_LANGUAGE)
    # i18n middleware
    if lang not in translations:
        lang = DEFAULT_LANGUAGE
    app = I18NMiddleware(app, I18NPlugin(
        domain="messages", lang_code=lang, default=DEFAULT_LANGUAGE,
        locale_dir=os.path.join(BASE_DIR, "locale")
    ))

    # reporting middleware for all mounted apps
    app = ReportingMiddleware(app, sensitive_params=("key", "pass", "*password*"))
    app.install_dump_route(bottle.app())

    app = SessionMiddleware(app, args.session_timeout)

    return app
