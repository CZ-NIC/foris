import argparse
import bottle
import logging
import re
import typing

from foris import __version__
from foris.state import current_state
from foris.backend import Backend


def get_arg_parser():
    """
    Create ArgumentParser instance with Foris arguments.

    :return: instance of ArgumentParser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version=__version__)
    group = parser.add_argument_group("run server")
    group.add_argument("-H", "--host", default="0.0.0.0")
    group.add_argument("-p", "--port", type=int, default=8080)
    group.add_argument("--session-timeout", type=int, default=900,
                       help="session timeout (in seconds)")
    group.add_argument("-s", "--server", choices=["wsgiref", "flup", "cgi"], default="wsgiref")
    group.add_argument("-d", "--debug", action="store_true")
    group.add_argument("--noauth", action="store_true",
                       help="disable authentication (available only in debug mode)")
    parser.add_argument("-R", "--routes", action="store_true", help="print routes and exit")
    group.add_argument(
        "-S", "--static", action="store_true",
        help="serve static files directly through foris app (should be used for debug only)"
    )
    group.add_argument(
        "-a", "--app", choices=["config"], default="config",
        help="sets which app should be started (config/...)",
    )
    group.add_argument(
        "-b", "--message-bus", choices=["ubus", "unix-socket", "mqtt"], default="ubus",
        help="message bus type"
    )
    group.add_argument(
        "--mqtt-port", default=1883, type=int, help="mqtt port (default 1883)"
    )
    group.add_argument(
        "--mqtt-host", default="localhost", help="mqtt host (default 'localhost')"
    )
    group.add_argument(
        "--mqtt-passwd-file", type=lambda x: read_passwd_file(x),
        help="path to passwd file (first record will be used to authenticate)",
        default=None,
    )
    group.add_argument(
        "--bus-socket", default="/var/run/ubus.sock", help="message bus socket path"
    )
    group.add_argument(
        "--ws-port", default=0, help="websocket server port - insecure (0=autodetect)", type=int
    )
    group.add_argument(
        "--wss-port", default=0, help="websocket server port - secure (0=autodetect)", type=int
    )
    group.add_argument(
        "--ws-path", default="/foris-ws", help="websocket server url path - insecure", type=str,
    )
    group.add_argument(
        "--wss-path", default="/foris-ws", help="websocket server url path - secure", type=str,
    )
    group.add_argument(
        "-A", "--assets", default="/tmp/.foris_workdir/dynamic_assets",
        help="Path where dynamic foris assets will be generated."
    )

    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    # setup logging
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    logger = logging.getLogger("foris")
    logger.debug("Version %s" % __version__)

    # set backend
    if args.message_bus in ["ubus", "unix-socket"]:
        current_state.set_backend(Backend(args.message_bus, path=args.bus_socket))
    elif args.message_bus == "mqtt":
        current_state.set_backend(
            Backend(
                args.message_bus, host=args.mqtt_host, port=args.mqtt_port,
                credentials=args.mqtt_passwd_file
            )
        )

    # update websocket
    current_state.set_websocket(args.ws_port, args.ws_path, args.wss_port, args.wss_path)
    # set assets path
    current_state.set_assets_path(args.assets)

    if args.app == "config":
        from foris.config_app import prepare_config_app
        main_app = prepare_config_app(args)

    if args.routes:
        # routes should be printed and we can safely exit
        return True

    # run the right server
    if args.server == "wsgiref":
        bottle.run(app=main_app, host=args.host, port=args.port, debug=args.debug)
    elif args.server == "flup":
        # bindAddress is None - FCGI process must be spawned by the server
        bottle.run(app=main_app, server="flup", debug=args.debug, bindAddress=None)
    elif args.server == "cgi":
        bottle.run(app=main_app, server="cgi", debug=args.debug)


def read_passwd_file(path: str) -> typing.Tuple[str]:
    """ Returns username and password from passwd file
    """
    with open(path, "r") as f:
        return re.match(r"^([^:]+):(.*)$", f.readlines()[0][:-1]).groups()


if __name__ == "__main__":
    main()
