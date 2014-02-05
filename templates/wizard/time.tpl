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

%if form:
    <form class="wizard-form" action="{{ url("wizard_step", number=4) }}" method="post" novalidate>
        <h1>{{ trans(first_title) }}</h1>
        <p class="wizard-description">{{ first_description }}</p>
        %include _messages
        <div class="form-fields">
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include _field field=field
        %end
        </div>

        <div id="wizard-time-sync">
            <a href="#" id="wizard-time-sync-auto" class="button">{{ trans("Synchronize with your computer clock") }}</a>
            <a href="#" id="wizard-time-sync-manual" class="button">{{ trans("Set time manually") }}</a>
            <p id="wizard-time-sync-success">{{ trans("Synchronization successful.") }}</p>
        </div>

        <button class="button-next" type="submit" name="send" class="button-arrow-right">{{ trans("Next") }}</button>
    </form>
%else:
    <div id="wizard-time">
        <h1>{{ trans("Time settings") }}</h1>
        <div id="time-progress" class="background-progress">
            <img src="{{ static("img/loader.gif") }}" alt="{{ trans("Loading...") }}"><br>
            {{ trans("Synchronizing router time with an internet time server.") }}<br>
            {{ trans("One moment, please...")  }}
        </div>

        <div id="time-success">
            <img src="{{ static("img/success.png") }}" alt="{{ trans("Done") }}"><br>
            <p>{{ trans("Time was successfully synchronized, you can move to the next step.") }}</p>
            <a class="button-next" href="{{ next_step_url }}">{{ trans("Next") }}</a>
        </div>
    </div>

    <script>
        $(document).ready(function(){
            Foris.ntpUpdate();
        });
    </script>
%end