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

# builtins
import logging
import os

# 3rd party
import bottle

# local
from foris.config import init_app as init_app_config, top_index

from foris.common import render_js_md5
from foris.common_app import prepare_common_app
from foris.utils import contract_valid


logger = logging.getLogger("foris.config")

BASE_DIR = os.path.dirname(__file__)


bottle.SimpleTemplate.defaults['contract_valid'] = contract_valid
bottle.SimpleTemplate.defaults['js_md5'] = lambda filename: render_js_md5(filename)


def prepare_config_app(args):
    """
    Prepare Foris main application - i.e. apply CLI arguments, mount applications,
    install hooks and middleware etc...

    :param args: arguments received from ArgumentParser.parse_args().
    :return: bottle.app() for Foris
    """
    return prepare_common_app(args, "config", init_app_config, top_index, logger)
