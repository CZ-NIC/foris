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
import random
import string


def update_csrf_token(save_session=True):
    """Generate new CSRF token, assign it to a template variable and save it to session.

    This should be called on every login.
    """
    def generate_token():
        return "".join(random.choice(string.ascii_letters + string.digits) for i in range(32))

    session = bottle.request.environ['beaker.session']
    session['csrf_token'] = bottle.SimpleTemplate.defaults['csrf_token'] = generate_token()
    if save_session:
        session.save()


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
        bottle.SimpleTemplate.defaults['csrf_token'] = None

    def apply(self, callback, route):
        # make CSRF protection implicitly enabled (since it's more fool-proof)
        disable_csrf_protect = route.config.get("disable_csrf_protect", False)

        session = bottle.request.environ['beaker.session']
        valid_token = session.get("csrf_token")
        if not valid_token:
            update_csrf_token()

        if bottle.SimpleTemplate.defaults['csrf_token'] is None:
            bottle.SimpleTemplate.defaults['csrf_token'] = valid_token

        if disable_csrf_protect or bottle.request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            return callback

        def wrapper(*args, **kwargs):
            token = None
            if bottle.request.method == "POST":
                token = bottle.request.POST.get("csrf_token")
            # do not refer session from outer scope! we need to get new value
            # in each call of the function
            session = bottle.request.environ['beaker.session']
            if not token or token != session.get("csrf_token"):
                bottle.abort(403, "CSRF token validation failed.")

            return callback(*args, **kwargs)
        return wrapper
