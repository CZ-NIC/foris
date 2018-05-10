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

import os
import bottle
import logging

from bottle_i18n import I18NMiddleware, I18NPlugin, i18n_defaults

from foris.common import init_common_app, init_default_app
from foris.langs import DEFAULT_LANGUAGE
from foris.middleware.backend_data import BackendData
from foris.middleware.sessions import SessionMiddleware
from foris.middleware.reporting import ReportingMiddleware
from foris.plugins import ForisPluginLoader
from foris.state import current_state
from foris.utils.bottle_stuff import (
    prepare_template_defaults,
    route_list_cmdline,
    route_list_debug,
)
from foris.utils import messages

BASE_DIR = os.path.dirname(__file__)


def prepare_common_app(args, app_name, init_function, top_index, logger, load_plugins=True):
    """
    Prepare Foris application - i.e. apply CLI arguments, mount applications,
    install hooks and middleware etc...

    :param args: arguments received from ArgumentParser.parse_args().
    :param app_name: the name of the application
    :type app_name: str
    :param init_function: function to init the routes (app specific)
    "type init_function: callable
    :return: bottle.app() for Foris
    """

    # set app
    current_state.set_app(app_name)

    # internationalization
    i18n_defaults(bottle.SimpleTemplate, bottle.request)

    # setup default template defaults
    prepare_template_defaults()

    # init messaging template
    messages.set_template_defaults()

    app = init_default_app(top_index, args.static)

    # basic and bottle settings
    template_dir = os.path.join(BASE_DIR, "templates")
    bottle.TEMPLATE_PATH.append(template_dir)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    # mount apps
    app.mount("/main", init_function())

    if args.debug:
        if args.noauth:
            logger.warning("authentication disabled")
            app.config["no_auth"] = True

    # set custom app attributes for main app and all mounted apps
    init_common_app(app, None)
    for route in app.routes:
        if route.config.get("mountpoint"):
            mounted = route.config['mountpoint.target']
            prefix = route.config['mountpoint.prefix']
            init_common_app(mounted, prefix)

    if load_plugins:
        # load Foris plugins before applying Bottle plugins to app
        loader = ForisPluginLoader(app)
        loader.autoload_plugins()

    # i18n middleware
    app = I18NMiddleware(app, I18NPlugin(
        domain="messages", lang_code=DEFAULT_LANGUAGE, default=DEFAULT_LANGUAGE,
        locale_dir=os.path.join(BASE_DIR, "locale")
    ))

    # obtains required data from backend (this will happen everytime when a request arrives)
    app = BackendData(app)

    # reporting middleware for all mounted apps
    app = ReportingMiddleware(app, sensitive_params=("key", "pass", "*password*"))
    app.install_dump_route(bottle.app())

    # session handling
    app = SessionMiddleware(app, args.session_timeout)

    # print routes to console and exit
    if args.routes:
        routes = route_list_cmdline(bottle.app())
        print("\n".join(sorted(set(routes))))
        return app

    # print routes in debug mode
    if args.debug:
        routes = route_list_debug(bottle.app())
        logger.debug("Routes:\n%s", "\n".join(routes))

    return app
