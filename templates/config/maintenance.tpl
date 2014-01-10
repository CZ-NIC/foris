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

<div id="page-maintenance">
    <h2>{{ _("Maintenance") }}</h2>
    <div class="maintenance-description">
        <a href="{{ url("config_action", page_name="maintenance", action="config-backup") }}" class="button">{{ _("Download configuration backup") }}</a>
        <a href="{{ url("config_action", page_name="maintenance", action="reboot") }}" class="button">{{ _("Reboot") }}</a>
    </div>

    <form id="main-form" class="maintenance-form" action="{{ request.fullpath }}" method="post" enctype="multipart/form-data" autocomplete="off" {{! form.render_html_data() }}>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include config/_field field=field
        %end
        <button type="submit" name="send" class="button">{{ trans("Restore from backup") }}</button>
    </form>

</div>
