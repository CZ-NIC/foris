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
from foris.nuci.client import contract_valid
from functools import wraps


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
