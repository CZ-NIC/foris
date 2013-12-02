%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2013 CZ.NIC, z.s.p.o. <www.nic.cz>
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
%if not defined('is_xhr'):
    %rebase _layout **locals()
    <div id="config-header">
        <h1>{{ _("Settings") }}</h1>
        <div class="logo-turris"><img src="{{ static("img/logo-turris.png") }}"></div>
        <a id="logout" href="{{ url("logout") }}">{{ _("Log out") }}</a>
    </div>


    <div id="config-content">

    <ul class="tabs">
        %for config_page in config_pages:
            <li \\
%if defined("active_config_page_key") and config_page['slug'] == active_config_page_key:
class="active" \\
%end\\
><a href="{{ url("config_page", page_name=config_page['slug']) }}">{{ _(config_page['name']) }}</a></li>
        %end
    </ul>
%end

    %include

%if not defined('is_xhr'):
    </div>
%end