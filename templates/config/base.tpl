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
%if not defined('is_xhr'):
    %rebase("_layout.tpl", **locals())
    <div id="header">
        <div class="sidebar-content">
            <a href="{{ url("config_index") }}"><img src="{{ static("img/logo-side-%LANG%.svg") }}" alt="{{ trans("Foris - administration interface of router Turris") }}" class="header-side" width="180"></a>
            <div class="header-top">
              <a href="#menu" class="menu-link"><img src="{{ static("img/icon-menu.png") }}" alt="{{ trans("Menu") }}" title="{{ trans("Menu") }}"></a>
              <a href="{{ url("config_index") }}"><img src="{{ static("img/logo-top-%LANG%.svg") }}" alt="{{ trans("Foris - administration interface of router Turris") }}" width="240"></a>
            </div>
        </div>
    </div>
    <div id="content-wrap">
        <div id="content">
          <h1>{{ title }}</h1>
%end
            {{! base }}
%if not defined('is_xhr'):
        </div>
    </div>
    <div id="menu">
        <div class="sidebar-content">
            <nav>
                <ul>
                %for slug, config_page in config_pages.iteritems():
                    <li{{! ' class="active"' if defined("active_config_page_key") and slug == active_config_page_key else "" }}>
                      <a href="{{ url("config_page", page_name=slug) }}">{{ trans(config_page.userfriendly_title) }}</a>
                    </li>
                %end
                </ul>
            </nav>

            <div id="subnav">
                <div id="language-switch">
                  <a href="{{ url("change_lang", lang="cs", backlink=request.fullpath) }}">CZE</a>
                  / <a href="{{ url("change_lang", lang="en", backlink=request.fullpath) }}">ENG</a>
                </div>
                <a id="logout" href="{{ url("logout") }}">{{ trans("Log out") }}</a>
            </div>
        </div>
    </div>
    <div class="sidebar-cleaner"></div>
    <div id="footer">
        <div class="sidebar-content">
            <img src="{{ static("img/logo-turris.svg") }}" alt="{{ trans("Project:Turris") }}" width="178">
        </div>
    </div>
%end