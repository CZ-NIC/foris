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

# 3rd party
import bottle
from bottle_i18n import I18NMiddleware, I18NPlugin, i18n_defaults

# local
from foris.wizard import init_app as init_app_wizard, top_index

from foris.common import render_js_md5, init_common_app, init_default_app
from foris.middleware.sessions import SessionMiddleware
from foris.middleware.reporting import ReportingMiddleware
from foris.nuci import client
from foris.langs import DEFAULT_LANGUAGE
from foris.plugins import ForisPluginLoader
from foris.state import current_state
from foris.utils import messages, contract_valid
from foris.utils.translators import translations, get_current_language
from foris.utils.bottle_stuff import (
    prepare_template_defaults,
    route_list_cmdline,
    route_list_debug,
)


logger = logging.getLogger("foris.wizard")

BASE_DIR = os.path.dirname(__file__)


bottle.SimpleTemplate.defaults['contract_valid'] = contract_valid
bottle.SimpleTemplate.defaults['js_md5'] = lambda filename: render_js_md5(filename)


def prepare_wizard_app(args):
    """
    Prepare Foris wizard application - i.e. apply CLI arguments, mount applications,
    install hooks and middleware etc...

    :param args: arguments received from ArgumentParser.parse_args().
    :return: bottle.app() for Foris
    """

    # set app
    current_state.set_app("wizard")

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
    app.mount("/main", init_app_wizard())

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
    lang = get_current_language()
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
