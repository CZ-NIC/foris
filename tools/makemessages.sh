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

if [[ ! $# -eq 4 ]]; then
	lang=$2
	locale_dir="$1/locale/$lang/LC_MESSAGES"
	pot="$1/locale/foris.pot"
	if [ ! -d $locale_dir ]
	then
		mkdir -p $locale_dir
	fi
	find $1 \( -iname "*.py" -o -iname "*.tpl" \) -exec cat {} \; | sed 's/"\?{{!* \(_\|trans\|\(\w*\)gettext\)\((".*")\|(''.*'')\).*}}"\?/\n\2gettext\3\n#/g' | \
		xgettext --package-name="$3" -d messages --no-location --language=Python --from-code=UTF-8 --output="$pot" -
	find $1 -iname "*.tpl" -exec sh -c 'grep -zq "%include.*_(" $0 && echo "WARNING: _() after %include in $0"' {} \;
	if [ -f $locale_dir/foris.po ]
	then
		echo "Making messages in $locale_dir."
		msgmerge -q -U $locale_dir/foris.po "$pot"
	else
		msginit -i "$pot" -l $lang --no-translator -o $locale_dir/foris.po
	fi
	echo "Message making completed."
else
    echo "$1 -- $2"
	>&2 echo "Usage: $0 PATH LANGUAGE PACKAGE"
fi
