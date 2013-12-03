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
    <form class="wizard-form" action="{{ url("wizard_step", number=3) }}" method="post" {{! form.render_html_data() }}>
        <h1>{{ first_title }}</h1>
        <p class="wizard-description">{{ first_description }}</p>
        <div class="form-fields">
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
        </div>

        <div id="wizard-time-sync">
            <a href="#" id="wizard-time-sync-auto" class="button">{{ _("Synchronize with your computer clock") }}</a>
            <a href="#" id="wizard-time-sync-manual" class="button">{{ _("Set time manually") }}</a>
            <p id="wizard-time-sync-success">{{ _("Synchronization successful.") }}</p>
        </div>

        <button class="button-next" type="submit" name="send" class="button-arrow-right">{{ _("Next") }}</button>
    </form>
%else:
    <div id="wizard-time">
        <h1>{{ _("Time settings") }}</h1>
        <div id="time-progress" class="background-progress">
            <img src="{{ static("img/loader.gif") }}" alt="{{ _("Loading...") }}"><br>
            {{ _("Synchronizing router time with an internet time server.") }}<br>
            {{ _("One moment, please...")  }}
        </div>

        <div id="time-success">
            <img src="{{ static("img/success.png") }}" alt="{{ _("Done") }}"><br>
            <p>{{ _("Time was successfully synchronized, you can move to the next step.") }}</p>
            <a class="button-next" href="{{ url("wizard_step", number=4) }}">{{ _("Next") }}</a>
        </div>
    </div>

    <script>
        $(document).ready(function(){
            ForisWizard.ntpUpdate();
        });
    </script>
%end