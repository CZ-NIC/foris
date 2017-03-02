#!/bin/bash
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

shopt -s extglob

for lang_dir in $1/locale/??; do
	locale_dir=${lang_dir}/LC_MESSAGES
	files=$(find ${locale_dir} -name "*.po" -not -name "messages.po")
	msgcat ${files} > ${locale_dir}/messages.po
	echo "Compiling translation files in $lang_dir."
	msgfmt ${locale_dir}/messages.po -o ${locale_dir}/messages.mo
done
echo "All messages compiled."
