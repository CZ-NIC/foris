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

<h1>{{ trans("Registration failure") }}</h1>

<p>
{{ trans("Unfortunately, it wasn't possible to generate the registration code. This usually means the router is not connected to the internet. Please, try registering later. If the problem persists, contact the support.") }}
</p>

%if len(notifications):
    <h2>{{ trans("Important updates") }}</h2>
    <p>{{! trans("Important updates that require a device restart have been installed. Some services might not work if you don't restart the device. For details see below.")  }}</p>
    %include _notifications.tpl notifications=notifications
%end

<a class="button-next" href="{{ url("config_index") }}">{{ trans("Continue to configuration interface") }}</a>