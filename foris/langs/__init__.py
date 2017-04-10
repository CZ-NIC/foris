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

import os
import pkgutil


# english is default
DEFAULT_LANGUAGE = 'en'
iso2to3 = {'en': 'eng'}
translation_names = {'en': 'English'}
translations = []

for loader, name, _ in pkgutil.iter_modules([os.path.dirname(__file__)]):
    module = loader.find_module(name).load_module(name)
    translations.append(module.iso2)
    iso2to3[module.iso2] = module.iso3
    translation_names[module.iso2] = module.name

translations.sort()
translations.insert(0, DEFAULT_LANGUAGE)  # english first
