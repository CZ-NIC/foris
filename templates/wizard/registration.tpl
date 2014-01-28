%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
%#
%# This program is free software: you can redistribute it and/or modify
%# it under the terms of the GNU General Public License as published by
%# the Free Software Foundation, either version 3 of the License, or
%# (at your option) any later version.
%#
%# This program is distributed in the hope that it will be useful,
%# but WITHOUT ANY WARRANTY; without even the implied warranty of
%# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%# GNU General Public License for more details.
%#
%# You should have received a copy of the GNU General Public License
%# along with this program.  If not, see <http://www.gnu.org/licenses/>.
%#
%rebase wizard/base **locals()

<h1>{{ trans("Device registration") }}</h1>

<p>
    {{! _("Device was succesfully installed. Last step that is required is a registration of your device in your user profile on the Turris site <a href=\"%(url)s\">%(url)s</a>.") % {'url': "https://www.turris.cz/user/register-router"} }}
</p>
<p class="activation-code">{{ code }}</p>
<p>{{! _("<strong>Warning:</strong> this code has a limited validity. In case this code is refused, refresh this page to get a new one.") }}</p>
<p>{{! _("Any of these settings can be set in the <a href=\"%(url)s\">configuration interface</a>. You can use it to activate LuCI interface for setting the advanced configuration.") % {'url': url("config_index")} }}</p>