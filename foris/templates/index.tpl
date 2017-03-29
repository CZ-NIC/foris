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
%rebase("_layout.tpl", **locals())
<div id="login-page">
    <div class="foris-version">
        <span class="minor-text">foris version: {{ foris_version }} </span>
    </div>
    <div class="language-switch">
      %include("_lang_flat", translations=translations, iso2to3=iso2to3)
    </div>

    <h1><img src="{{ static("img/logo-turris.svg") }}" alt="{{ trans("Project:Turris") }}" width="295"></h1>

    %include("_messages")

    %if user_authenticated():
        <a href="{{ url("logout") }}">{{ trans("Log out") }}</a>
    %else:
        <form action="{{ request.fullpath }}" method="POST">
            <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %if request.GET.get("next"):
            <input type="hidden" name="next" value="{{ request.GET['next'] }}">
        %end
            <label for="field-password">{{ trans("Password") }}</label>
            <input id="field-password" type="password" name="password" placeholder="{{ trans("Password") }}" autofocus>
            <button class="button" type="submit">{{ trans("Log in") }}</button>
        </form>
    %end
  <div class="footer">
    {{ trans("Foris Configuration Interface") }}<br>
    <a href="{{ luci_path }}">{{ trans("Go to LuCI") }}</a>
  </div>
</div>
