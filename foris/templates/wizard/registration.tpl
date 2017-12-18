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
%rebase("wizard/base", **locals())

<h1>{{ trans("Device registration") }}</h1>

<p>
    {{! trans("Device was successfully installed. Last step that is required is a registration of your device in your user profile on the Turris website <a href=\"%(url)s\">%(url)s</a>.") % {'url': "https://www.turris.cz/user/register-router"} }}
</p>
<p class="activation-code">{{ code }}</p>
<p>{{! trans("<strong>Warning:</strong> this code is valid only for limited time. In case this code is refused, refresh this page to get a new one.") }}</p>

<br />

<h2>{{ trans("What next?") }}</h2>

<p>{{! trans("You can change any of the previously configured settings in the <a href=\"%(url)s\">standard configuration interface</a>. In case you are interested in more advanced options, you can use the LuCI interface which is available from the <a href=\"%(url2)s\">Advanced administration tab</a>.") % {'url': helpers.external_url("config/"), 'url2': helpers.external_url("config/main/system-password/")} }}</p>

%if len(notifications):
    <h2>{{ trans("Important updates") }}</h2>
    <p>{{! trans("Important updates that require a device restart have been installed. Some services might not work if you don't restart the device. For details see below.")  }}</p>
    %include("_notifications.tpl", notifications=notifications)
%end

<a class="button-next" href="{{ helpers.external_url("config/") }}">{{ trans("Continue to the configuration interface") }}</a>
