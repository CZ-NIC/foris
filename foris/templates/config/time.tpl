%# Foris
%# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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
<div id="page-config" class="config-page">
%end
    <p class="config-description">{{ form.sections[0].description }}</p>
    <form id="time-form" class="config-form" action="{{ request.fullpath }}" method="post" autocomplete="off" novalidate>
        %include("_messages.tpl")
        <h3>{{ form.sections[0].sections[0].title}}</h3>
        <p class="config-description">{{ form.sections[0].sections[0].description }}</p>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.sections[0].sections[0].active_fields:
            %include("_field.tpl", field=field)
        %end
        <h3>{{ form.sections[0].sections[1].title}}</h3>
        <p class="config-description">{{ form.sections[0].sections[1].description }}</p>
        <div class="message error" id="ntp-error" >{{ trans("Failed to query ntp servers.") }}</div>
        %for field in form.sections[0].sections[1].active_fields:
            %include("_field.tpl", field=field)
        %end
        %if form.sections[0].sections[1].active_fields[0].field.get_value() == "ntp":
          <div class="row">
            <label for="field-time"><a href="#" class="button" id="start-ntpdate-button">{{ trans("Update time") }}</a></label>
            <input id="field-time" name="time" class="grayed" value="{{ form._request_data["time"] }}" disabled="1"></input>
            <img src="{{ static("img/icon-loading.gif") }}" class="field-loading" id="ntp-loading">
          </div>
        %end
        <div id="{{ 'form-%s-buttons' % form.name }}" class="form-buttons">
            <a href="{{ request.fullpath }}" class="button grayed">{{ trans("Discard changes") }}</a>
            <button type="submit" name="send" class="button">{{ trans("Save changes") }}</button>
        </div>
    </form>
%if not defined('is_xhr'):
</div>
<script>
    Foris.update_time = function(new_time) {
        $("#field-time").val(new_time);
    };
    Foris.display_ntpdate_error = function(show) {
        if (show) {
            $("#ntp-error").slideDown();
        } else {
            $("#ntp-error").slideUp();
        }
    };
    Foris.ntp_override = function() {
        $("#start-ntpdate-button").click(function(e) {
            Foris.display_ntpdate_error(false);
            var self = $(this);
            e.preventDefault();
            if (Foris.watched_ntpdate != null) {
                // already running
                return;
            };
            self.attr("disabled", "disabled");
            self.toggleClass("grayed");
            $.get('{{ url("config_ajax", page_name="time") }}', {action: "ntpdate-trigger"})
                    .done(function(response) {
                        Foris.watched_ntpdate = response.id;
                        $("#ntp-loading").show();
                    })
                    .fail(function(xhr) {
                        if (xhr.responseJSON && xhr.responseJSON.loggedOut && xhr.responseJSON.loginUrl) {
                            window.location.replace(xhr.responseJSON.loginUrl);
                            return;
                        }
                        Foris.display_ntpdate_error(true);
                        $("#start-ntpdate-button").toggleClass("grayed");
                    })
                    .always(function() {
                        self.removeAttr("disabled");
                    });
        });
    }
    Foris.afterAjaxUpdateFunctions.push(function(response, status, xhr) {
        Foris.ntp_override();
    });
    Foris.watched_ntpdate = null;
    Foris.WS["time"] = function(msg) {
        switch(msg["action"]) {
            case "ntpdate_started":
                if (msg.data.id != Foris.watched_ntpdate) {
                    break;
                }
                break;
            case "ntpdate_finished":
                if (msg.data.id != Foris.watched_ntpdate) {
                    break;
                }
                if (!msg.data.result) {
                    Foris.display_ntpdate_error(true);
                } else {
                    Foris.update_time(msg.data.time);
                }
                Foris.watched_ntpdate = null;
                $("#ntp-loading").hide();
                $("#start-ntpdate-button").toggleClass("grayed");
                break;
        }
    }
    $(document).ready(function() {
        Foris.ntp_override();
    });
</script>
%end
