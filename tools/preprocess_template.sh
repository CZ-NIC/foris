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

IFS=''
RELPATH='./foris/static/'

while read -r line; do
    if [[ $line != *MD5SUM* ]]
    then
        echo $line
    else
        filename=`echo $line | sed 's/.*static("\(.*\)").*/\1/'`
        hash=`md5sum $RELPATH$filename | cut -d ' ' -f 1`
        echo $line | sed "s/MD5SUM/$hash/"
    fi
done < $1
