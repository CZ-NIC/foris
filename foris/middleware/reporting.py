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

from fnmatch import fnmatch
from pprint import pformat
from traceback import format_exc

from bottle import _e, tob, html_escape, static_file

from foris.utils.routing import get_root
from foris.backend import ExceptionInBackend
from foris.state import current_state


ERROR_TEMPLATE = u"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Error | Administration interface of router Turris</title>
    <style>
    body, html {background-color: #eee; font-family: Helvetica, Arial, sans-serif;}
    #page {background-color: #fff; border: 1px solid #ccc; margin: 0 auto; padding: 1em; min-width: 60em; width: 90%%;}
    hr {border: 0; color: #999; background-color: #999; height: 1px;}
    p {line-height: 160%%;}
    pre {background-color: #fef9df; border: 1px solid #999; padding: 1em; margin: 1em;}
    .error {color: #c00;}
    </style>
</head>
<body>
    <div id="page">
        <h1>An unexpected error has occurred</h1>

        <p>We are sorry, but your request raised an unexpected error. More information about this error may be found below.</p>
        <p>If you are willing to help us with fixing of the problem, download the following <a href="%(dump_file)s">error protocol</a> and send it to us with a short description of the steps that led to the error to our email address <a href="mailto:tech.support@turris.cz">tech.support@turris.cz</a> (the protocol contains only a copy of the following informations).</p>
        <hr>

        <h1>Při zpracování požadavku došlo k chybě</h1>

        <p>Omlouváme se, ale během zpracování Vašeho požadavku došlo k nečekané chybě. Detailní informace naleznete níže.</p>
        <p>Pokud nám chcete pomoci s odstraněním chyby, stáhněte následující <a href="%(dump_file)s">protokol o chybě</a> a zašlete nám jej s krátkým popisem okolností vzniku chyby na adresu <a href="mailto:tech.support@turris.cz">tech.support@turris.cz</a> (protokol obsahuje pouze kopii informací uvedených na této stránce).</p>
        <hr>

        <h2 class="error">%(error)s</h2>
        %(extra)s
        <h3>Stack trace</h3>
        <pre>%(trace)s</pre>
        <h3>Environment</h3>
        <pre>%(environ)s</pre>
    </div>
</body>
</html>
"""


def filter_sensitive_params(params_dict, sensitive_params):
    for k, v in params_dict.items():
        for pattern in sensitive_params:
            if fnmatch(k, pattern):
                params_dict[k] = "**********"
    return params_dict


class ReportingMiddleware(object):
    def __init__(self, app, dump_file="foris-error.html", sensitive_params=None):
        """
        Initialize middleware for catching and reporting errors.

        :param app: instance of bottle application to apply this middleware to
        :param dump_file: filename of file with report which is saved to /tmp
        :param sensitive_params: list of sensitive params - supports shell-style wildcards
        """
        self.app = app
        self.dump_file = dump_file
        self.sensitive_params = sensitive_params or ()

    def __call__(self, environ, start_response):
        try:
            return self.app(environ, start_response)
        except (Exception, ExceptionInBackend) as e:
            template_vars = {}
            if 'bottle.request.post' in environ:
                environ['bottle.request.post'] = dict(
                    filter_sensitive_params(environ['bottle.request.post'],
                                            self.sensitive_params))
            # update environ
            environ["foris.version"] = current_state.foris_version
            environ["foris.language"] = current_state.language
            environ["foris.backend"] = current_state.backend

            template_vars['environ'] = html_escape(pformat(environ))
            # Handles backend exceptions in same manner as
            if isinstance(e, ExceptionInBackend):
                error = "Remote Exception: %s" % e.remote_description
                extra = "<h3>Remote request</h3><pre>%s</pre>" % html_escape(json.dumps(e.query))
                trace = e.remote_stacktrace
            else:
                error = repr(_e())
                trace = format_exc()
                extra = ""
            template_vars['error'] = html_escape(error)
            template_vars['trace'] = html_escape(trace)
            template_vars['extra'] = extra
            template_vars['dump_file'] = "%s/%s" % (get_root(), self.dump_file)
            environ['wsgi.errors'].write(format_exc())
            headers = [('Content-Type', 'text/html; charset=UTF-8')]
            err = ERROR_TEMPLATE % template_vars
            start_response('500 INTERNAL SERVER ERROR', headers)
            with open("/tmp/%s" % self.dump_file, "wb") as f:
                f.write(err.encode("UTF-8"))
            return [tob(err)]

    def install_dump_route(self, app):
        def foris_error():
            return static_file(
                self.dump_file, "/tmp", mimetype="text/plain", download=True)

        app.route("/%s" % self.dump_file, callback=foris_error)
