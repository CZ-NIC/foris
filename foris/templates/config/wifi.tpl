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

%if not defined('is_xhr'):
<div id="page-wifi" class="config-page">
%end
    %if not form or not len(form.active_fields):
    <div class="message warning">{{ trans("We were unable to detect any wireless cards in your router.") }}</div>
    %else:
    <p>{{! description }}</p>
    <form id="main-form" class="config-form config-form-wifi" action="{{ request.fullpath }}" method="post" autocomplete="off" novalidate>
        %include("_messages.tpl")
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %include("config/_wifi_form.tpl", form=form)
        <script src="{{ static("js/contrib/jquery.qrcode-0.7.0.min.js") }}"></script>
        <script>
            $(document).ready(function() {
                Foris.initWiFiQR();
            });
        </script>
        <div class="form-buttons">
            <a href="{{ request.fullpath }}" class="button grayed">{{ trans("Discard changes") }}</a>
            <button type="submit" name="send" class="button">{{ trans("Save changes") }}</button>
        </div>
    </form>
    %end
    <br />
    <div id="wifi-reset" class="config-description">
      <form id="wifi-reset-form" class="maintenance-form" method="post" action="{{ url("config_action", page_name="wifi", action="reset") }}">
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        <div class="row">
          <p>{{ trans("If a number of wireless cards doesn't match, you may try to reset the Wi-Fi settings. Note that this will remove the current Wi-Fi configuration and restore the default values.") }}</p>
          <button type="submit" name="send" class="button">{{ trans("Reset Wi-Fi settings") }}</button>
        </div>
      </form>
    </div>
%if not defined('is_xhr'):
</div>
%end
