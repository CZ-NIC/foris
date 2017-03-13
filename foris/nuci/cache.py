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

from datetime import datetime, timedelta

from .client import netconf
from .filters import create_uci_filter
from .modules.uci_raw import Uci


class NuciCache(object):
    """Nuci caching class

    It is used for explicit caching of values.
    """

    results = {}
    """
    records look like this
    'uci.foris.settings' : {
        'stored': datetime(year=2017,month=1,day=1,hour=0,minute=0,second=0),
        'data': YinElement
    }
    """

    def invalidate(self, path):
        """ Invalidates cache parts

        :param path: uci path which should be invalidated in cache
        """

        if not path:
            # remove all records
            self.results = {}

        self.results = {k: v for k, v in self.results.items() if not k.startswith(path)}

    def get(self, nuci_path, cache_valid_period):
        """ Get the record from the cache

        the old records are reobtained from nuci

        :param nuci_path: filter used to obtain the cache
        :type nuci_path: str
        :param cache_valid_period: older records are reloaded (in seconds), 0 means always reload
        :type cache_valid_period: int

         :returns: uci tree
         :rtype: YinElement
        """

        # try to return cached data
        if cache_valid_period and nuci_path in self.results:
            if self.results[nuci_path]['stored'] >= \
                    datetime.now() - timedelta(seconds=cache_valid_period):
                return self.results[nuci_path]['data']

        # create record
        splitted = nuci_path.split(".")
        if len(splitted) == 1:
            config, section, option = splitted[0], None, None
        elif len(splitted) == 2:
            config, section = splitted
            option = None
        else:
            config, section, option = splitted

        data = netconf.get(filter=("subtree", create_uci_filter(config, section, option))).data_ele
        uci_elem = data.find(Uci.qual_tag("uci"))
        if not uci_elem:
            return None

        data = Uci.from_element(data.find(Uci.qual_tag("uci")))
        self.results[nuci_path] = {'data': data, 'stored': datetime.now()}

        return data
