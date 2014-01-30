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
%rebase wizard/base **locals()

%if not form:
<h1>{{ first_title }}</h1>
<div class="message warning">{{ _("We were unable to detect any wireless cards in your router.") }}</div>
<form id="main-form" class="wizard-form wizard-form-wifi" action="{{ request.fullpath }}" method="post" autocomplete="off">
    <a href="{{ next_step }}" class="button-next button-arrow-right">{{ trans("Next") }}</a>
</form>
%else:
<form id="main-form" class="wizard-form wizard-form-wifi" action="{{ request.fullpath }}" method="post" autocomplete="off">
    <h1>{{ first_title }}</h1>
    <p class="wizard-description">{{! first_description }}</p>
    %include _messages
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    %for field in form.active_fields:
        %include _field field=field
    %end
    <div id="wifi-qr">
    </div>
    <script src="{{ static("js/contrib/jquery.qrcode-0.7.0.min.js") }}"></script>
    <script>
        $(document).ready(function() {
            ForisWizard.initWiFiQR();
        });
    </script>
    <button class="button-next button-arrow-right" type="submit" name="send">{{ trans("Next") }}</button>
</form>
%end