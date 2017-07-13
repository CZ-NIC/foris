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
import collections
import gettext
import hashlib
import logging
import os
import re
import time

# 3rd party
import bottle
from bottle_i18n import I18NMiddleware, I18NPlugin, i18n_defaults
from ncclient.operations import TimeoutExpiredError, RPCError

# local
from . import __version__ as foris_version
from .middleware.sessions import SessionMiddleware
from .nuci import client, filters, cache
from .nuci.modules.uci_raw import Uci, Config, Section, Option
from .nuci.modules.user_notify import Severity
from .langs import iso2to3, translation_names, translations, DEFAULT_LANGUAGE
from .plugins import ForisPluginLoader
from .utils import (
    redirect_unauthenticated, is_safe_redirect, is_user_authenticated, template_helpers, LazyCache
)
from .utils.bottle_csrf import get_csrf_token, update_csrf_token, CSRFValidationError, CSRFPlugin
from .utils import DEVICE_CUSTOMIZATION, messages, contract_valid
from .utils.reporting_middleware import ReportingMiddleware
from .utils.routing import reverse, static


logger = logging.getLogger("foris")

BASE_DIR = os.path.dirname(__file__)

# init cache
nuci_cache = cache.NuciCache()
lazy_cache = LazyCache()

# internationalization
i18n_defaults(bottle.SimpleTemplate, bottle.request)

# read locale directory
locale_directory = os.path.join(BASE_DIR, "locale")

translations = collections.OrderedDict(
    (e, gettext.translation("messages", locale_directory, languages=[e], fallback=True))
    for e in translations
)

ugettext = lambda x: translations[bottle.request.app.lang].ugettext(x)
ungettext = lambda singular, plural, n: translations[bottle.request.app.lang].ungettext(singular, plural, n)
bottle.SimpleTemplate.defaults['trans'] = lambda msgid: ugettext(msgid)  # workaround
bottle.SimpleTemplate.defaults['translation_names'] = translation_names
bottle.SimpleTemplate.defaults['translations'] = [e for e in translations]
bottle.SimpleTemplate.defaults['iso2to3'] = iso2to3
bottle.SimpleTemplate.defaults['ungettext'] = lambda singular, plural, n: ungettext(singular, plural, n)
bottle.SimpleTemplate.defaults['DEVICE_CUSTOMIZATION'] = DEVICE_CUSTOMIZATION
bottle.SimpleTemplate.defaults['contract_valid'] = contract_valid
bottle.SimpleTemplate.defaults['foris_version'] = foris_version
gettext_dummy = lambda x: x
_ = ugettext

# template defaults
# this is not really straight-forward, check for user_authenticated() (with brackets) in template,
# because bool(user_authenticated) is always True - it means bool(<function ...>)
bottle.SimpleTemplate.defaults["user_authenticated"] =\
    lambda: bottle.request.environ["foris.session"].get("user_authenticated")
bottle.SimpleTemplate.defaults["request"] = bottle.request
bottle.SimpleTemplate.defaults["url"] = lambda name, **kwargs: reverse(name, **kwargs)
bottle.SimpleTemplate.defaults["static"] = static
bottle.SimpleTemplate.defaults["get_csrf_token"] = get_csrf_token
bottle.SimpleTemplate.defaults["helpers"] = template_helpers

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


def login_redirect(step_num, wizard_finished=False):
    from wizard import NUM_WIZARD_STEPS
    if step_num >= NUM_WIZARD_STEPS or wizard_finished:
        next = bottle.request.GET.get("next")
        if next and is_safe_redirect(next, bottle.request.get_header('host')):
            bottle.redirect(next)
        bottle.redirect(reverse("config_index"))
    elif step_num == 1:
        bottle.redirect(reverse("wizard_index"))
    else:
        bottle.redirect(reverse("wizard_step", number=step_num))


@bottle.view("index")
def index():
    session = bottle.request.environ['foris.session']
    import wizard
    allowed_step_max, wizard_finished = wizard.get_wizard_progress()

    if allowed_step_max == 1:
        if session.is_anonymous:
            session.recreate()
        session["user_authenticated"] = True
    else:
        session[wizard.WizardStepMixin.next_step_allowed_key] = str(allowed_step_max)
        session["wizard_finished"] = wizard_finished
        allowed_step_max = int(allowed_step_max)

    session.save()
    if session.get("user_authenticated"):
        login_redirect(allowed_step_max, wizard_finished)

    return dict(luci_path="//%(host)s/%(path)s"
                          % {'host': bottle.request.get_header('host'), 'path': 'cgi-bin/luci'})


def render_js(filename):
    """ Render javascript template to insert a translation
        :param filename: name of the file to be translated
    """

    headers = {}

    # check the template file
    path = bottle.SimpleTemplate.search("javascript/%s" % filename, bottle.TEMPLATE_PATH)
    if not path:
        return bottle.HTTPError(404, "File does not exist.")

    # test last modification date (mostly copied from bottle.py)
    stats = os.stat(path)
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    headers['Last-Modified'] = lm

    ims = bottle.request.environ.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = bottle.parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        return bottle.HTTPResponse(status=304, **bottle.response.headers)

    # set the content type to javascript
    headers['Content-Type'] = "application/javascript; charset=UTF-8"

    body = bottle.template("javascript/%s" % filename)
    # TODO if you are sadistic enough you can try to minify the content

    return bottle.HTTPResponse(body, **headers)


def render_js_md5(filename):
    # calculate the hash of the rendered template
    return hashlib.md5(bottle.template("javascript/%s" % filename).encode('utf-8')).hexdigest()


bottle.SimpleTemplate.defaults['js_md5'] = lambda filename: render_js_md5(filename)


def change_lang(lang):
    """Change language of the interface.

    :param lang: language to set
    :raises: bottle.HTTPError if requested language is not installed
    """
    if lang in translations:
        bottle.request.app.lang = lang
        write_uci_lang(lang)
        backlink = bottle.request.GET.get('backlink')
        if backlink and is_safe_redirect(backlink, bottle.request.get_header('host')):
            bottle.redirect(backlink)
        bottle.redirect(reverse("index"))
    else:
        raise bottle.HTTPError(404, "Language '%s' is not available." % lang)


def read_uci_lang(default):
    """Read interface language saved in Uci config foris.settings.lang.

    :param default: returned if no language is set in the config
    :return: language code of interface language
    """
    data = client.get(filter=filters.foris_config)
    lang = data.find_child("uci.foris.settings.lang")
    if lang is None:
        return default
    return lang.value


def write_uci_lang(lang):
    """Save interface language to foris.settings.lang.

    :param lang: language code to save
    :return: True on success, False otherwise
    """
    uci = Uci()
    # Foris language
    foris = Config("foris")
    uci.add(foris)
    server = Section("settings", "config")
    foris.add(server)
    server.add(Option("lang", lang))
    # LuCI language
    luci = Config("luci")
    uci.add(luci)
    main = Section("main", "core")
    luci.add(main)
    main.add(Option("lang", lang))
    try:
        client.edit_config(uci.get_xml())
        return True
    except (RPCError, TimeoutExpiredError):
        return False


def login():
    session = bottle.request.environ["foris.session"]

    next = bottle.request.POST.get("next")
    if _check_password(bottle.request.POST.get("password")):
        # re-generate session to prevent session fixation
        session.recreate()
        session["user_authenticated"] = True

        update_csrf_token(save_session=False)
        session.save()
        if next and is_safe_redirect(next, bottle.request.get_header('host')):
            bottle.redirect(next)

        # update contract status
        client.update_contract_status()
        nuci_cache.invalidate("foris.contract")

    else:
        messages.error(_("The password you entered was not valid."))

    if next:
        redirect = "/?next=%s" % next
        if is_safe_redirect(redirect, bottle.request.get_header('host')):
            bottle.redirect(redirect)
    bottle.redirect(reverse("index"))


def logout():
    session = bottle.request.environ["foris.session"]

    if "user_authenticated" in session:
        session.load_anonymous()

    bottle.redirect(reverse("index"))


def static(filename):
    """ return static file
    :param filename: url path
    :type filename: str
    :return: http response
    """

    if not bottle.DEBUG:
        logger.warning("Static files should be handled externally in production mode.")

    match = re.match(r'/*plugins/+(\w+)/+(.+)', filename)
    if match:
        plugin_name, plugin_file = match.groups()

        # find correspoding plugin
        for plugin in bottle.app().foris_plugin_loader.plugins:
            if plugin.PLUGIN_NAME == plugin_name:
                return bottle.static_file(
                    plugin_file, root=os.path.join(plugin.DIRNAME, "static"))

    return bottle.static_file(filename, root=os.path.join(os.path.dirname(__file__), "static"))


def _check_password(password):
    import pbkdf2
    data = client.get(filter=filters.foris_config)
    password_hash = data.find_child("uci.foris.auth.password")
    if password_hash is None:
        # consider unset password as successful auth
        # maybe set some session variable in this case
        return True
    password_hash = password_hash.value
    # crypt automatically extracts salt and iterations from formatted pw hash
    return password_hash == pbkdf2.crypt(password, salt=password_hash)


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


def make_notification_title(notification):
    """
    Helper function for creating of human-readable notification title.

    :param notification: notification to create title for
    :return: translated string with notification title
    """
    notification_titles = {
        Severity.NEWS: _("News"),
        Severity.UPDATE: _("Update"),
        Severity.ERROR: _("Error"),
    }

    # minor abuse of gettext follows...
    locale_date = notification.created_at.strftime(_("%Y/%m/%d %H:%M:%S"))

    return _("%(notification)s from %(created_at)s") % dict(
        notification=notification_titles.get(notification.severity.value, _("Notification")),
        created_at=locale_date
    )


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
    import config
    import wizard
    app.mount("/config", config.init_app())
    app.mount("/wizard", wizard.init_app())

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
