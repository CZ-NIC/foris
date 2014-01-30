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
    <h2>{{ trans("Maintenance") }}</h2>
    %include _messages

    <h3>{{ trans("Configuration backup") }}</h3>
    <p>{{ trans("If you need to save the current configuration of this device, you can download a backup file. Configuration is saved as an unencrypted compressed archive (.tar.xz). Password for this configuration interface and for the advanced configuration is not included in the backup.") }}</p>
    <div class="maintenance-description">
        <a href="{{ url("config_action", page_name="maintenance", action="config-backup") }}" class="button">{{ trans("Download configuration backup") }}</a>
    </div>

    <h3>{{ trans("Configuration restore") }}</h3>
    <p>{{ trans("To restore the configuration from a backup file, upload it using following form. Keep in mind that IP address of this device might change during the process, causing unavailability of this interface.") }}</p>
    <form id="main-form" class="maintenance-form" action="{{ request.fullpath }}" method="post" enctype="multipart/form-data" autocomplete="off" novalidate>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include _field field=field
        %end
        <button type="submit" name="send" class="button">{{ trans("Restore from backup") }}</button>
    </form>


    <h3>{{ trans("Device reboot") }}</h3>
    <p>{{ trans("If you need to reboot the device, click on the following button. The reboot process takes approximately 30 seconds, you will be required to log in again when the router comes up.") }}</p>
    <div>
        <a href="{{ url("config_action", page_name="maintenance", action="reboot") }}" class="button">{{ trans("Reboot") }}</a>
    </div>
</div>
