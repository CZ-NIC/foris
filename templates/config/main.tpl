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
%rebase config/base **locals()

<form id="main-form" class="config-form" action="{{ request.fullpath }}" method="post" autocomplete="off" {{! form.render_html_data() }}>
    <p class="config-description">{{! description }}</p>
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    %for field in form.active_fields:
        %if field.hidden:
            {{! field.render() }}
        %else:
        <div>
            {{! field.label_tag }}
            {{! field.render() }}
            %if field.hint:
                <img class="field-hint" src="{{ static("img/icon-help.png") }}" title="{{ field.hint }}">
            %end
        </div>
        %end
    %end
    <div class="form-buttons">
        <a href="{{ request.fullpath }}" type="submit" class="button grayed">{{ _("Discard changes") }}</a>
        <button type="submit" name="send" class="button">{{ _("Save changes") }}</button>
    </div>
</form>