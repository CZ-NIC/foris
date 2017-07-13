# coding=utf-8
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
import json
import urlparse

from datetime import datetime, timedelta

import bottle
from functools import wraps
import logging
from xml.etree import cElementTree as ET

from .routing import reverse
from .. import DEVICE_CUSTOMIZATION
from ..nuci.modules.uci_raw import parse_uci_bool


logger = logging.getLogger("foris.utils")


def is_user_authenticated():
    session = bottle.request.environ['foris.session']
    return session.get("user_authenticated", False)


def redirect_unauthenticated(redirect_url=None):
    redirect_url = redirect_url or reverse("index")
    no_auth = bottle.default_app().config.get("no_auth", False)
    if not no_auth and not is_user_authenticated():
        from foris.core import ugettext as _
        import messages
        messages.info(_("You have been logged out due to longer inactivity."))
        if bottle.request.is_xhr:
            # "raise" JSON response if requested by XHR
            res = bottle.response.copy(cls=bottle.HTTPResponse)
            res.content_type = 'application/json'
            res.body = json.dumps(dict(success=False, loggedOut=True, loginUrl=redirect_url))
            res.status = 403
            raise res
        # "raise" standard bottle redirect
        login_url = "%s?next=%s" % (redirect_url, bottle.request.fullpath)
        bottle.redirect(login_url)


def contract_valid():
    """Read whether the contract related with the current router is valid from uci

    :return: whether the contract is still valid
    """
    if DEVICE_CUSTOMIZATION == "omnia":
        return False

    from foris.core import nuci_cache
    data = nuci_cache.get("foris.contract", 60 * 60)  # once per hour should be enought
    valid = data.find_child("foris.contract.valid")

    if not valid:  # valid record
        # valid record not found, assuming that the contract is still valid
        return True

    return parse_uci_bool(valid)


def login_required(func=None, redirect_url=None):
    """Decorator for views that require login.

    :param redirect_url:
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        redirect_unauthenticated(redirect_url)
        return func(*args, **kwargs)
    return wrapper


def is_safe_redirect(url, host=None):
    """
    Checks if the redirect URL is safe, i.e. it uses HTTP(S) scheme
    and points to the host specified.

    Also checks for presence of newlines to avoid CRLF injection.

    :param url: URL to check
    :param host: host that has to match the URL's host, if specified
    :return:
    """
    if "\r" in url or "\n" in url:
        logger.warning("Possible CRLF injection attempt: \n%s", bottle.request.environ)
        return False
    url_components = urlparse.urlparse(url)
    return ((not url_components.scheme or url_components.scheme in ['http', 'https'])
            and (not url_components.netloc or url_components.netloc == host))


def require_customization(required_customization=None):
    """
    Decorator for methods that require specific DEVICE_CUSTOMIZATION value.
    Raises bottle HTTPError if current DEVICE_CUSTOMIZATION differs.

    :param required_customization: required device customization string
    :return: decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if DEVICE_CUSTOMIZATION != required_customization:
                raise bottle.HTTPError(403, "Requested method is not available in this Foris build.")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_contract_valid(valid=True):
    """
    Decorator for methods that require valid contract.
    Raises bottle HTTPError if validity differs.

    :param valid: should be contrat valid
    :type valid: bool
    :return: decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not (contract_valid() == valid):
                raise bottle.HTTPError(403, "Contract validity mismatched.")
            return func(*args, **kwargs)
        return wrapper
    return decorator


class Lazy(object):
    def __init__(self, func):
        self.func = func
        self.value = None

    def __call__(self):
        if self.value is None:
            self.value = self.func()
        return self.value

    def __getattr__(self, item):
        if self.value is None:
            self.value = self.func()
        return getattr(self.value, item)


class LazyCache(object):
    """
    Simple per request cache of lazy objects
    """
    def __init__(self):
        self.clear()

    def __getattr__(self, name):
        res = self._attr_dict[name]
        logger.debug("Lazy cache object '%s' obtained." % name)
        return res

    def __setattr__(self, name, func):
        if not callable(func):
            raise TypeError("Expected callable")
        self._attr_dict[name] = Lazy(func)
        logger.debug("Lazy cache object '%s' initialized." % name)

    def __delattr__(self, name):
        del self._attr_dict[name]
        logger.debug("Lazy cache object '%s' removed." % name)

    def clear(self):
        super(LazyCache, self).__setattr__('_attr_dict', {})


def localized_sorted(iterable, lang, cmp=None, key=None, reverse=False):
    """
    Sorted method that can sort according to a language-specific alphabet.

    :param iterable: iterable to sort
    :param lang: alphabet to use
    :param cmp: cmp argument for the sorted method
    :param key: key argument for the sorted method
    :param reverse: reverse argument for the sorted method
    :return: sorted iterable
    """
    alphabet = {
        # FIXME: "ch" should be sorted after h in Czech
        'cs': u" AÁÅBCČDĎEÉĚFGHIÍJKLMNŇOÓPQRŘSŠTŤUÚŮVWXYÝZŽ"
              u"aáåbcčdďeéěfghiíjklmnňoópqrřsštťuúůvwxyýzž"
    }

    alphabet = alphabet.get(lang)
    if not alphabet:
        return sorted(iterable, cmp, key, reverse)

    key = key or (lambda x: x)

    def safe_index(c):
        """Get index of a character in the alphabet, do not raise error."""
        try:
            return alphabet.index(c)
        except ValueError:
            return len(alphabet) + ord(c)

    def key_fn(x):
        """Key function for sorting using a custom alphabet."""
        return map(safe_index, key(x))

    return sorted(iterable, cmp, key_fn, reverse)
