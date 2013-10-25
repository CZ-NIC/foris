#!/usr/bin/env python

import bottle
import logging
from nuci import client
import os
import sys
import uci
import wizard


logger = logging.getLogger("foris")

#def set_template_defaults(template):
#    template.defaults.update({
#        'url': lambda *args, **kwargs: get_url(*args, **kwargs),
#        'static': lambda filename: get_url("static", filename=filename)
#    })
#
#set_template_defaults(bottle.SimpleTemplate)


@bottle.route("/")
@bottle.view("index")
def index():
    pass


@bottle.route('/static/<filename:re:.*>', name="static")
def static(filename):
    if not bottle.DEBUG:
        logger.warning("Static files should be handled externally in production mode.")
    return bottle.static_file(filename, root=os.path.join(os.path.dirname(__file__), "static"))


# ---------------------------------------------------------------------------- #
#                                      MAIN                                    #
# ---------------------------------------------------------------------------- #
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", choices=["wsgiref", "flup"], default="wsgiref")
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument("--nucipath", help="path to Nuci binary")
    args = parser.parse_args()

    # basic and bottle settings
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    bottle.TEMPLATE_PATH.append(template_dir)
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    app = bottle.app()
    app.mount("/wizard", wizard.app)

    if args.debug:
        # "about:config" is available only in debug mode
        app.mount("/uci", uci.app)
        # for nice debugging and profiling, try importing FireLogger support
        try:
            from firepython.middleware import FirePythonWSGI
            app = FirePythonWSGI(app)
        except ImportError:
            firepython = None

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