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

import foris.config as config_app
import foris.wizard as wizard_app

# 3rd party
import bottle
from bottle_i18n import I18NMiddleware, I18NPlugin, i18n_defaults

# local
from .common import (
    index, login, foris_403_handler, render_js_md5, render_js, logout, change_lang, static
)
from .middleware.sessions import SessionMiddleware
from .middleware.reporting import ReportingMiddleware
from .nuci import client
from .nuci.helpers import contract_valid, read_uci_lang
from .langs import DEFAULT_LANGUAGE
from .plugins import ForisPluginLoader
from .middleware.bottle_csrf import CSRFPlugin
from .utils import messages
from .utils.translators import translations
from .utils.bottle_stuff import (
    prepare_template_defaults,
    clickjacking_protection,
    clear_lazy_cache,
    disable_caching,
    route_list_cmdline,
    route_list_debug,
)


logger = logging.getLogger("foris")

BASE_DIR = os.path.dirname(__file__)


bottle.SimpleTemplate.defaults['contract_valid'] = contract_valid
bottle.SimpleTemplate.defaults['js_md5'] = lambda filename: render_js_md5(filename)


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

    # internationalization
    i18n_defaults(bottle.SimpleTemplate, bottle.request)

    # setup default template defaults
    prepare_template_defaults()

    # init messaging template
    messages.set_template_defaults()

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
