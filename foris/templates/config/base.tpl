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
            <a href="{{ url("config_index") }}">
                <img src="{{ static("img/logo-turris.svg") }}" alt="{{ trans("Foris - administration interface of router Turris") }}" class="header-side" height="65">
            </a>
            <div class="config-foris-version">
                %include("_foris_version.tpl")
            </div>
            <div class="header-top">
              <a href="#menu" class="menu-link"><img src="{{ static("img/icon-menu.png") }}" alt="{{ trans("Menu") }}" title="{{ trans("Menu") }}"></a>
              <a href="{{ url("config_index") }}"><img src="{{ static("img/logo-turris.svg") }}" alt="{{ trans("Foris - administration interface of router Turris") }}" height="50"></a>
            </div>
        </div>
    </div>
    <div id="content-wrap">
        <div id="content">
          %if foris_info.guide.enabled:
          <div id="guide-box">
            <p class="guide-title">{{ trans("foris guide") }}</p>
            %for msg in foris_info.guide.message(active_config_page_key):
            <p>{{ msg }}</p>
            %end
            <div class="guide-buttons">
              <form method="post" action="{{ url("leave_guide") }}">
                <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
                <button type="submit" name="target" class="button" value="save">{{ trans("Leave Guided Mode") }}</button>
              </form>
              %if foris_info.guide.current != active_config_page_key:
              <a class="button" href="{{ url("config_page", page_name=foris_info.guide.current) }}">{{ trans("Next step") }} ➡</a>
              %end
            </div>
          </div>
          %end
          <div id="network-restart-notice" class="main-warning-notice">
            <img src="{{ static("img/loader.gif") }}" alt="{{ trans("Network is restarting...") }}" title="{{ trans("Network is restarting...") }}">
            <span>{{ trans("Your network is being restarted. Wait, please...") }}</span>
          </div>
          <div id="rebooting-notice" class="main-warning-notice">
            <img src="{{ static("img/loader.gif") }}" alt="{{ trans("Rebooting...") }}" title="{{ trans("Rebooting...") }}">
            <span>{{ trans("Your router is being rebooted.") }}</span>
          </div>
    %if foris_info.reboot_required:
          <div id="reboot-required-notice" style='display: block'>
    %else:
          <div id="reboot-required-notice" style='display: none'>
    %end
            <div id="reboot-required-button-container">
              <span>{{ trans("Your router needs to be restarted in order to work properly.") }}</span>
              <a href="{{ url("reboot")}}" class="button" id="reboot-required-button">{{ trans("Reboot now") }}</a>
            </div>
          </div>
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
                %for slug, config_page, menu_tag in config_pages.menu_list():
                    %if foris_info.guide.is_available(slug):
                    <li{{! ' class="active"' if defined("active_config_page_key") and slug == active_config_page_key else "" }}>
                      <a href="{{ url("config_page", page_name=slug) }}">{{ trans(config_page.userfriendly_title) }}
                      % show = menu_tag["show"] or foris_info.guide.enabled and slug == foris_info.guide.current
                      <span title="{{ menu_tag["hint"]}}" style="{{"" if show else "display: none" }}" id="{{ slug }}_menu_tag" class="menu-tag">
                        {{ "⬅" if foris_info.guide.enabled and slug == foris_info.guide.current else menu_tag["text"] }}
                      </span>
                      </a>
                    </li>
                    %end
                %end
                </ul>
            </nav>

            <div id="subnav">
              <div id="logout">
                <a href="{{ url("logout") }}">{{ trans("Log out") }}</a>
              </div>
              <div id="language-switch">
                %if translations == ["en"] and lang() == "en":
                <a href="{{ url("config_page", page_name="updater") }}#language-install">{{ translation_names.get("en") }}</a>
                %else:
                <span>{{ translation_names.get(lang(), lang()) }}</span>
                %end
                <ul>
                  %for code in translations:
                    %if code != lang():
                      <li><a href="{{ url("change_lang", lang=code, backlink=request.fullpath) }}">{{ translation_names.get(code, code) }}</a></li>
                    %end
                  %end
                </ul>
              </div>
            </div>
        </div>
    </div>
    <div class="sidebar-cleaner"></div>
%end
