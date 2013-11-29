#!/usr/bin/env python
from beaker.middleware import SessionMiddleware
import bottle
from bottle_i18n import I18NMiddleware, I18NPlugin, i18n_defaults
import gettext
import logging
from nuci import client, filters
import os
import sys
from utils.routing import reverse


logger = logging.getLogger("foris")

BASE_DIR = os.path.dirname(__file__)

# internationalization
LANGUAGE = 'cs' # hardcoded for now, use session or better uci or $LANG to store the value
i18n_defaults(bottle.SimpleTemplate, bottle.request)
trans = gettext.translation("messages", os.path.join(BASE_DIR, "locale"), languages=[LANGUAGE], fallback=True)
gettext = trans.ugettext

# template defaults
# this is not really straight-forward, check for user_authenticated() (with brackets) in template,
# because bool(user_authenticated) is always True - it means bool(<function ...>)
bottle.SimpleTemplate.defaults["user_authenticated"] =\
    lambda: bottle.request.environ["beaker.session"].get("user_authenticated")
bottle.SimpleTemplate.defaults["request"] = bottle.request
bottle.SimpleTemplate.defaults["url"] = lambda name, **kwargs: reverse(name, **kwargs)
bottle.SimpleTemplate.defaults["static"] = lambda filename, *args: reverse("static", filename=filename) % args


def login_redirect(step_num):
    NUM_WIZZARD_STEPS = 7
    if step_num >= NUM_WIZZARD_STEPS:
        bottle.redirect(reverse("config_index"))
    else:
        bottle.redirect(reverse("wizard_step", number=step_num))


@bottle.route("/", name="index")
@bottle.view("index")
def index():
    session = bottle.request.environ['beaker.session']
    import wizard
    allowed_step_max = wizard.get_allowed_step_max()
    
    if not allowed_step_max:
        session["user_authenticated"] = True
        allowed_step_max = 1
    else:
        session[wizard.WizardStepMixin.next_step_allowed_key] = str(allowed_step_max)
        allowed_step_max = int(allowed_step_max)
    
    session.save()
    if session.get("user_authenticated"):
        login_redirect(allowed_step_max)
    
    return dict()


@bottle.route("/", method="POST", name="login")
def login():
    session = bottle.request.environ["beaker.session"]
    if _check_password(bottle.request.POST.get("password")):
        session["user_authenticated"] = True
        session.save()
        next = bottle.request.POST.get("next")
        if next:
            bottle.redirect(next)

    bottle.redirect("/")


@bottle.route("/logout", name="logout")
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
    from beaker.crypto import pbkdf2
    data = client.get(filter=filters.uci)
    password_hash = data.find_child("uci.foris.auth.password")
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
    app = I18NMiddleware(app, I18NPlugin(domain="messages", lang_code=LANGUAGE, default="en",
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
        'session.type': 'file',
        'session.data_dir': '/tmp/beaker/data',
        'session.lock_dir': '/tmp/beaker/lock',
        'session.cookie_expires': True,
        'session.timeout': 600,
    }
    app = SessionMiddleware(app, session_options)

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
