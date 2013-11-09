import bottle
import logging

logger = logging.getLogger("utils.routing")


def reverse(name, **kargs):
    try:
        return bottle.app().router.build(name, **kargs)
    except bottle.RouteBuildError:
        for route in bottle.app().routes:
            if route.config.get("mountpoint"):
                mountpoint = route.config['mountpoint']
                try:
                    return "%s%s" % (mountpoint['prefix'].rstrip("/"),
                                     mountpoint['target'].router.build(name, **kargs))
                except bottle.RouteBuildError:
                    pass
    raise bottle.RouteBuildError("No route with name '%s' in main app or mounted apps." % name)