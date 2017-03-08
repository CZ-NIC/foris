import bottle

from foris.core import get_arg_parser, prepare_main_app


def main():
    parser = get_arg_parser()
    args = parser.parse_args()

    main_app = prepare_main_app(args)

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
