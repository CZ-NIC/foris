#!/usr/bin/env python
from beaker.middleware import SessionMiddleware
import bottle
from bottle_i18n import I18NMiddleware, I18NPlugin, i18n_defaults
import gettext
import logging
from nuci import client, filters
import os
import sys


logger = logging.getLogger("foris")

BASE_DIR = os.path.dirname(__file__)

# i18n-related, hardcoded for now
i18n_defaults(bottle.SimpleTemplate, bottle.request)
trans = gettext.translation("messages", os.path.join(BASE_DIR, "locale"), languages=["cs"])
gettext = trans.ugettext

# template defaults
# this is not really straight-forward, check for user_authenticated() (with brackets) in template,
# because bool(user_authenticated) is always True - it means bool(<function ...>)
bottle.SimpleTemplate.defaults["user_authenticated"] =\
    lambda: bottle.request.environ["beaker.session"].get("user_authenticated")
bottle.SimpleTemplate.defaults["request"] = bottle.request

@bottle.route("/")
@bottle.view("index")
def index():
    return dict()


@bottle.route("/", method="POST")
def login():
    session = bottle.request.environ["beaker.session"]
    if _check_password(bottle.request.POST.get("password")):
        session["user_authenticated"] = True
        session.save()
        bottle.redirect("/")
    bottle.redirect("/")


@bottle.route("/logout")
def logout():
    session = bottle.request.environ["beaker.session"]
    if "user_authenticated" in session:
        del session["user_authenticated"]
        session.save()
    bottle.redirect("/")


@bottle.route('/static/<filename:re:.*>', name="static")
def static(filename):
    if not bottle.DEBUG:
        logger.warning("Static files should be handled externally in production mode.")
    return bottle.static_file(filename, root=os.path.join(os.path.dirname(__file__), "static"))


def _check_password(password):
    import pbkdf2
    data = client.get(filter=filters.uci)
    password_hash = data.find_child("uci.cznic.foris.password")
    if password_hash is None:
        # consider unset password as successful auth
        # maybe set some session variable in this case
        return True
    password_hash = password_hash.value
    # crypt automatically extracts salt and iterations from formatted pw hash
    return password_hash == pbkdf2.crypt(password, salt=password_hash)

# ---------------------------------------------------------------------------- #
#                                      MAIN                                    #
# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", choices=["wsgiref", "flup"], default="wsgiref")
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("--noauth", action="store_true",
                        help="disable authentication (available only in debug mode)")
    parser.add_argument("--nucipath", help="path to Nuci binary")
    args = parser.parse_args()

    # basic and bottle settings
    template_dir = os.path.join(BASE_DIR, "templates")
    bottle.TEMPLATE_PATH.append(template_dir)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    app = bottle.app()
    # mount apps
    import config
    import wizard
    app.mount("/config", config.app)
    app.mount("/wizard", wizard.app)
    if args.debug:
        # "about:config" is available only in debug mode
        import uci
        # must be mounted before wrapping the app with middleware
        app.mount("/uci", uci.app)
        if args.noauth:
            logger.warning("authentication disabled")
            app.config.no_auth = True

    # i18n middleware
    app = I18NMiddleware(app, I18NPlugin(domain="messages", lang_code="cs", default="cs",
                                         locale_dir=os.path.join(BASE_DIR, "locale")))

    if args.debug:
        # for nice debugging and profiling, try importing FireLogger support
        try:
            from firepython.middleware import FirePythonWSGI
            app = FirePythonWSGI(app)
        except ImportError:
            FirePythonWSGI = None

    # session middleware (note: session.auto does not work within Bottle)
    session_options = {
        'session.type': 'memory',
        'session.cookie_expires': True,
        'session.timeout': 600,
    }
    app = SessionMiddleware(app)

    # there are some threading-related errors caused by an issue in
    # Python <= 2.7.3 (Python issue #14308), this monkey-patch fixes them
    if sys.hexversion <= 0x020703f0:
        import threading
        threading._DummyThread._Thread__stop = lambda x: 42

    if args.nucipath:
        client.set_bin_path(args.nucipath)

    # run the right server
    if args.server == "wsgiref":
        bottle.run(app=app, host="0.0.0.0", port=8080, debug=args.debug)
    elif args.server == "flup":
        # bindAddress is None - FCGI process must be spawned by the server
        bottle.run(app=app, server="flup", debug=args.debug, bindAddress=None)