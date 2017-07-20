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
import hashlib
import logging
import pbkdf2
import os
import re
import time

from functools import wraps

from foris.nuci import client, filters
from foris.nuci.helpers import write_uci_lang, contract_valid
from foris.caches import nuci_cache
from foris.utils import (
    redirect_unauthenticated, is_safe_redirect, messages, login_required
)
from foris.middleware.bottle_csrf import update_csrf_token, CSRFValidationError, CSRFPlugin
from foris.utils.routing import reverse
from foris.utils.translators import _, translations
from foris.utils.bottle_stuff import (
    clickjacking_protection,
    clear_lazy_cache,
    disable_caching,
)


logger = logging.getLogger("foris.common")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def _check_password(password):
    data = client.get(filter=filters.foris_config)
    password_hash = data.find_child("uci.foris.auth.password")
    if password_hash is None:
        # consider unset password as successful auth
        # maybe set some session variable in this case
        return True
    password_hash = password_hash.value
    # crypt automatically extracts salt and iterations from formatted pw hash
    return password_hash == pbkdf2.crypt(password, salt=password_hash)


def login():
    session = bottle.request.environ["foris.session"]

    next = bottle.request.POST.get("next")
    if _check_password(bottle.request.POST.get("password")):
        # re-generate session to prevent session fixation
        session.recreate()
        session["user_authenticated"] = True

        update_csrf_token(save_session=False)
        session.save()
        if next and is_safe_redirect(next, bottle.request.get_header('host')):
            bottle.redirect(next)

        # update contract status
        client.update_contract_status()
        nuci_cache.invalidate("foris.contract")

    else:
        messages.error(_("The password you entered was not valid."))

    if next:
        redirect = "/?next=%s" % next
        if is_safe_redirect(redirect, bottle.request.get_header('host')):
            bottle.redirect(redirect)
    bottle.redirect(reverse("index"))


def logout():
    session = bottle.request.environ["foris.session"]

    if "user_authenticated" in session:
        session.load_anonymous()

    bottle.redirect(reverse("index"))


def foris_403_handler(error):
    if isinstance(error, CSRFValidationError):
        try:
            # maybe the session expired, if so, just redirect the user
            redirect_unauthenticated()
        except bottle.HTTPResponse as e:
            # error handler must return the exception, otherwise it would
            # be raised and not handled by Bottle
            return e

    # otherwise display the standard error page
    bottle.app().default_error_handler(error)


def render_js(filename):
    """ Render javascript template to insert a translation
        :param filename: name of the file to be translated
    """

    headers = {}

    # check the template file
    path = bottle.SimpleTemplate.search("javascript/%s" % filename, bottle.TEMPLATE_PATH)
    if not path:
        return bottle.HTTPError(404, "File does not exist.")

    # test last modification date (mostly copied from bottle.py)
    stats = os.stat(path)
    lm = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime))
    headers['Last-Modified'] = lm

    ims = bottle.request.environ.get('HTTP_IF_MODIFIED_SINCE')
    if ims:
        ims = bottle.parse_date(ims.split(";")[0].strip())
    if ims is not None and ims >= int(stats.st_mtime):
        headers['Date'] = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        return bottle.HTTPResponse(status=304, **bottle.response.headers)

    # set the content type to javascript
    headers['Content-Type'] = "application/javascript; charset=UTF-8"

    body = bottle.template("javascript/%s" % filename)
    # TODO if you are sadistic enough you can try to minify the content

    return bottle.HTTPResponse(body, **headers)


def render_js_md5(filename):
    # calculate the hash of the rendered template
    return hashlib.md5(bottle.template("javascript/%s" % filename).encode('utf-8')).hexdigest()


def change_lang(lang):
    """Change language of the interface.

    :param lang: language to set
    :raises: bottle.HTTPError if requested language is not installed
    """
    if lang in translations:
        write_uci_lang(lang)
        backlink = bottle.request.GET.get('backlink')
        if backlink and is_safe_redirect(backlink, bottle.request.get_header('host')):
            bottle.redirect(backlink)
        bottle.redirect(reverse("index"))
    else:
        raise bottle.HTTPError(404, "Language '%s' is not available." % lang)


def static(filename):
    """ return static file
    :param filename: url path
    :type filename: str
    :return: http response
    """

    if not bottle.DEBUG:
        logger.warning("Static files should be handled externally in production mode.")

    match = re.match(r'/*plugins/+(\w+)/+(.+)', filename)
    if match:
        plugin_name, plugin_file = match.groups()

        # find correspoding plugin
        for plugin in bottle.app().foris_plugin_loader.plugins:
            if plugin.PLUGIN_NAME == plugin_name:
                return bottle.static_file(
                    plugin_file, root=os.path.join(plugin.DIRNAME, "static"))

    return bottle.static_file(filename, root=os.path.join(BASE_DIR, "static"))


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


@login_required
def reboot():
    client.reboot()
    bottle.redirect(reverse("/"))


def init_default_app(index, include_static=False):
    """
    Initialize top-level Foris app - register all routes etc.

    :param include_static: include route to static files
    :type include_static: bool
    :return: instance of Foris Bottle application
    """

    app = bottle.app()
    app.install(CSRFPlugin())
    app.route("/", name="index", callback=index)
    app.route("/lang/<lang:re:\w{2}>", name="change_lang", callback=change_lang)
    app.route("/", method="POST", name="login", callback=login)
    app.route("/logout", name="logout", callback=logout)
    app.route("/reboot", name="reboot", callback=reboot)
    if include_static:
        app.route('/static/<filename:re:.*>', name="static", callback=static)
    app.route("/js/<filename:re:.*>", name="render_js", callback=render_js)
    return app


def init_common_app(app, prefix):
    """
    Initializes Foris application - use this method to apply properties etc.
    that should be set to main app and all the mounted apps (i.e. to the
    Bottle() instances).


    :param app: instance of bottle application to mount
    :param prefix: prefix which has been used to mount the application
    """
    app.catchall = False  # caught by ReportingMiddleware
    app.error_handler[403] = foris_403_handler
    app.add_hook('after_request', clickjacking_protection)
    app.add_hook('after_request', disable_caching)
    app.add_hook('after_request', clear_lazy_cache)
    app.config['prefix'] = prefix
