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


import bottle

from foris.langs import iso2to3, translation_names
from foris.middleware.bottle_csrf import get_csrf_token
from foris.state import current_state

from .routing import reverse, static as static_path
from .translators import translations, ugettext, ungettext
from . import is_user_authenticated, template_helpers


def prepare_template_defaults():
    bottle.SimpleTemplate.defaults['trans'] = lambda msgid: ugettext(msgid)  # workaround
    bottle.SimpleTemplate.defaults['translation_names'] = translation_names
    bottle.SimpleTemplate.defaults['translations'] = [e for e in translations]
    bottle.SimpleTemplate.defaults['iso2to3'] = iso2to3
    bottle.SimpleTemplate.defaults['ungettext'] = \
        lambda singular, plural, n: ungettext(singular, plural, n)
    bottle.SimpleTemplate.defaults['foris_info'] = current_state

    # template defaults
    # this is not really straight-forward, check for user_authenticated() (with brackets) in template,
    # because bool(user_authenticated) is always True - it means bool(<function ...>)
    bottle.SimpleTemplate.defaults["user_authenticated"] =\
        lambda: bottle.request.environ["foris.session"].get("user_authenticated")
    bottle.SimpleTemplate.defaults["request"] = bottle.request
    bottle.SimpleTemplate.defaults["url"] = lambda name, **kwargs: reverse(name, **kwargs)
    bottle.SimpleTemplate.defaults["static"] = static_path
    bottle.SimpleTemplate.defaults["get_csrf_token"] = get_csrf_token
    bottle.SimpleTemplate.defaults["helpers"] = template_helpers


def disable_caching(authenticated_only=True):
    """
    Hook for disabling caching.

    :param authenticated_only: apply only if user is authenticated
    """
    if not authenticated_only or authenticated_only and is_user_authenticated():
        bottle.response.headers['Cache-Control'] = "no-store, no-cache, must-revalidate, " \
                                                   "no-transform, max-age=0, post-check=0, pre-check=0"
        bottle.response.headers['Pragma'] = "no-cache"


def clickjacking_protection():
    # we don't use frames at all, we can safely deny opening pages in frames
    bottle.response.headers['X-Frame-Options'] = 'DENY'


def clear_lazy_cache():
    from foris.caches import lazy_cache
    lazy_cache.clear()


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
