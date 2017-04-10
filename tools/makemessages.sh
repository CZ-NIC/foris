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

set -e

function make_pot() {
	local path="$1"
	local package="$2"
	local output="$3"
	echo "Creating/overriding pot file in '$output'."
	find "$path" \( -iname "*.py" -o -iname "*.tpl" \) -exec cat {} \; | sed 's/"\?{{!* \(_\|trans\|\(\w*\)gettext\)\((".*")\|(''.*'')\).*}}"\?/\n\2gettext\3\n#/g' | \
		xgettext --package-name="$package" -d messages --no-location --language=Python --from-code=UTF-8 --output="$output" -
	find $1 -iname "*.tpl" -exec sh -c 'grep -zq "%include.*_(" $0 && echo "WARNING: _() after %include in $0"' {} \;
}

function make_po() {
	local locale_dir="$1"
	local pot_path="$2"
	local lang="$3"
	if [ -f $locale_dir/foris.po ]
	then
		echo "Merging messages in '$locale_dir'."
		msgmerge -q -U "$locale_dir"/foris.po "$pot_path"
	else
		echo "Creating messages in '$locale_dir'."
		msginit -i "$pot_path" -l $lang --no-translator -o "$locale_dir"/foris.po
	fi
}

function make_messages() {
	local path="$1"
	local package="$2"
	local lang="$3"
	local locale_dir="$path/locale/$lang/LC_MESSAGES"
	local pot_path="$path/locale/foris.pot"

	[ -d "$locale_dir" ] || mkdir -p "$locale_dir"
	make_pot "$path" "$package" "$pot_path"
	make_po "$locale_dir" "$pot_path" "$lang"
}

if [ $# -eq 3 ]; then
	make_messages "$1" "${2:-Foris}" "$3"
	echo "Message making completed."
elif [ $# -lt 3 -a $# -gt 0 ]; then
	for dir in "$1"/locale/?? ; do
		make_messages "$1" "${2:-Foris}" "$(basename "$dir")"
	done
else
	echo "Usage: $0 PATH [PACKAGE [LANGUAGE]] "
fi
