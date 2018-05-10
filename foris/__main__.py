import argparse
import bottle

from foris.state import current_state
from foris.backend import Backend


def get_arg_parser():
    """
    Create ArgumentParser instance with Foris arguments.

    :return: instance of ArgumentParser
    """
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
    parser.add_argument("-R", "--routes", action="store_true", help="print routes and exit")
    group.add_argument(
        "-S", "--static", action="store_true",
        help="serve static files directly through foris app (should be used for debug only)"
    )
    group.add_argument(
        "-a", "--app", choices=["config", "wizard"], default="config",
        help="sets which app should be started (wizard/config)",
    )
    group.add_argument(
        "-b", "--backend", choices=["ubus", "unix-socket"], default="ubus", help="backend type"
    )
    group.add_argument(
        "--backend-socket", default="/var/run/ubus.sock", help="backend socket path"
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

    return parser


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    # set backend
    current_state.set_backend(Backend(args.backend, args.backend_socket))
    # update websocket
    current_state.set_websocket(args.ws_port, args.ws_path, args.wss_port, args.wss_path)

    if args.app == "config":
        from foris.config_app import prepare_config_app
        main_app = prepare_config_app(args)
    elif args.app == "wizard":
        from foris.wizard_app import prepare_wizard_app
        main_app = prepare_wizard_app(args)

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


if __name__ == "__main__":
    main()
