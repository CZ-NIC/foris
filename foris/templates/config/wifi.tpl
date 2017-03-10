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
    %if not form:
    <div class="message warning">{{ trans("We were unable to detect any wireless cards in your router.") }}</div>
    %else:
    <form id="main-form" class="config-form config-form-wifi" action="{{ request.fullpath }}" method="post" autocomplete="off" novalidate>
        <p class="config-description">{{! description }}</p>
        %include("_messages.tpl")
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include("_field.tpl", field=field)
            %if field.name == "radio0-hwmode" and DEVICE_CUSTOMIZATION == "omnia" and field.field.value == "11g":
                <div class="row">
                    <p class="form-note">
                    {{ trans("If you want to use this card for 2.4GHz bands, correction of cables connected to diplexers is needed! Factory default setting: Cables from big card connected to 5GHz, cables from small card connected to 2.4GHz diplexer part.") }}
                    <p>
               </div>
            %end
        %end
        <div id="wifi-qr">
        </div>
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
%if not defined('is_xhr'):
</div>
%end
