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
%rebase("config/base.tpl", **locals())

<div id="page-maintenance" class="config-page">
    %include("_messages.tpl")

    <h2>{{ trans("Notifications and automatic restarts") }}</h2>
    <p>{{ trans("You can set the router to notify you when a specific event occurs, for example when a reboot is required, no space is left on device or an application update is installed. You can use Turris servers to send these emails. Alternatively, if you choose to use a custom server, you must enter some additional settings. These settings are the same as you enter in your email client and you can get them from the provider of your email inbox. In that case, because of security reasons, it is recommended to create a dedicated account for your router.") }}</p>
    <p>{{ trans("Also, when an automatic restart is required, you can specify the time you want it to occur. If you have email notifications enabled, you can also specify the interval between notification and automatic restart.") }}</p>
    <form id="notifications-form" class="maintenance-form" action="{{ url("config_action", page_name="maintenance", action="save_notifications") }}" method="post" enctype="multipart/form-data" autocomplete="off" novalidate>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for section in notifications_form.sections:
            %if section.active_fields:
                <h4>{{ section.title }}</h4>
                %for field in section.active_fields:
                    %include("_field.tpl", field=field)
                %end
            %end
        %end
        <button type="submit" name="send" class="button">{{ trans("Save") }}</button>
        %if notifications_form.data['enable_smtp']:
            <button id="notifications-test" type="submit" name="action" value="test_notifications" class="button">{{ trans("Send testing message") }}</button>
        %end
    </form>

    <h2>{{ trans("Configuration backup") }}</h2>
    <p>{{ trans("If you need to save the current configuration of this device, you can download a backup file. The configuration is saved as an unencrypted compressed archive (.tar.bz2). Passwords for this configuration interface and for the advanced configuration are not included in the backup.") }}</p>
    <div class="maintenance-description">
        <a href="{{ url("config_action", page_name="maintenance", action="config-backup") }}" class="button">{{ trans("Download configuration backup") }}</a>
    </div>

    <h2>{{ trans("Configuration restore") }}</h2>
    <p>{{ trans("To restore the configuration from a backup file, upload it using following form. Keep in mind that IP address of this device might change during the process, causing unavailability of this interface.") }}</p>
    <form id="restore-form" class="maintenance-form" action="{{ request.fullpath }}" method="post" enctype="multipart/form-data" autocomplete="off" novalidate>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include("_field.tpl", field=field)
        %end
        <button type="submit" name="send" class="button">{{ trans("Restore from backup") }}</button>
    </form>

    <h2>{{ trans("Device reboot") }}</h2>
    <p>{{ trans("If you need to reboot the device, click on the following button. The reboot process takes approximately 30 seconds, you will be required to log in again after the reboot.") }}</p>
    <div>
        <a href="{{ url("reboot") }}" id="reboot-router" class="button">{{ trans("Reboot") }}</a>
    </div>

    <script>
      Foris.initNotificationTestAlert();
      $(document).ready(function() {
        $("#reboot-router").click(function(e) {
          var self = $(this);
          e.preventDefault();
            $.get('{{ url("reboot") }}')
              .done(function(response, status, xhr) {
                $("html, body").stop().animate({scrollTop:0}, 500, "swing");
            });
        });
      });
    </script>
</div>
