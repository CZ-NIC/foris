# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

import bottle
import string

from random import SystemRandom
random = SystemRandom()


def get_csrf_token():
    session = bottle.request.environ['foris.session']
    csrf_token = session.get("csrf_token")
    if not csrf_token:
        # create new token if it's not present in this session
        update_csrf_token()
    return session.get("csrf_token")


def update_csrf_token(save_session=True):
    """Generate new CSRF token, assign it to a template variable and save it to session.

    This should be called on every login.
    """
    def generate_token():
        return "".join(random.choice(string.ascii_letters + string.digits) for i in range(32))

    session = bottle.request.environ['foris.session']
    session['csrf_token'] = generate_token()
    if save_session:
        session.save()


class CSRFValidationError(bottle.HTTPError):
    def __init__(self, text="CSRF token validation failed."):
        super(CSRFValidationError, self).__init__(403, text)


class CSRFPlugin(object):
    """Bottle plugin for protection against CSRF attacks.

    CSRF protection is included in every request that is not safe (safe HTTP methods are
    defined in RFC 2616). To disable protection, set ``disable_csrf_protect`` attribute
    of route to True.

    This plugin uses sessions, Beaker session middleware is required.
    """
    name = "csrf"
    api = 2

    def setup(self, app):
        bottle.SimpleTemplate.defaults['get_csrf_token'] = get_csrf_token

    def apply(self, callback, route):
        # make CSRF protection implicitly enabled (since it's more fool-proof)
        disable_csrf_protect = route.config.get("disable_csrf_protect", False)

        if not get_csrf_token():
            update_csrf_token()

        if disable_csrf_protect or bottle.request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return callback

        def wrapper(*args, **kwargs):
            token = None
            if bottle.request.method == "POST":
                token = bottle.request.POST.get("csrf_token",
                                                bottle.request.headers.get("X-CSRFToken"))
            # do not refer session from outer scope! we need to get new value
            # in each call of the function
            if not token or token != get_csrf_token():
                raise CSRFValidationError()

            return callback(*args, **kwargs)
        return wrapper
