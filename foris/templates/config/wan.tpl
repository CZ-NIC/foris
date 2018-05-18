%# Foris - web administration interface for OpenWrt based on NETCONF
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
<div id="page-wan" class="config-page">
%end
    <form id="main-form" class="config-form" action="{{ request.fullpath }}" method="post" autocomplete="off" novalidate>
        <p class="config-description">{{! description }}</p>
        %include("_messages.tpl")
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include("_field.tpl", field=field)
        %end
        <div id="{{ 'form-%s-buttons' % form.name }}" class="form-buttons">
            <a href="{{ request.fullpath }}" class="button grayed">{{ trans("Discard changes") }}</a>
            <button type="submit" name="send" class="button">{{ trans("Save changes") }}</button>
        </div>
    </form>
%if not defined('is_xhr'):
    <h2>{{ trans("Connection test") }}</h2>
    <p>{{! trans("Here you can test you connection settings. Remember to click on the <strong>Save</strong> button before running the test. Note that sometimes it takes a while before the connection is fully initialized. So it might be useful to wait for a while before running this test.") }}</p>
    <div class="message error" id="connection-test-fail">
      {{ trans("Unable to verify network connection.") }}
    </div>
    <table id="test-results">
        <thead>
            <tr>
              <th>{{ trans("Test type") }}</th>
              <th>{{ trans("Status") }}</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>{{ trans("IPv4 connectivity") }}</td><td class="result" data-result-type="ipv4-conn-test">???</td></tr>
            <tr><td>{{ trans("IPv4 gateway connectivity") }}</td><td class="result" data-result-type="ipv4_gateway-conn-test">???</td></tr>
            %if form.current_data["wan6_proto"] != "none":
            <tr><td>{{ trans("IPv6 connectivity") }}</td><td class="result" data-result-type="ipv6-conn-test">???</td></tr>
            <tr><td>{{ trans("IPv6 gateway connectivity") }}</td><td class="result" data-result-type="ipv6_gateway-conn-test">???</td></tr>
            %end
        </tbody>
    </table>
    <a href="#" id="test-connection" class="button">{{ trans("Test connection") }}</a>
</div>
%end
<script>
    Foris.watched_test = null;
    var update_conn_test_field = function(key, result) {
        var field = key + "-conn-test";
        var resultBox = $("#test-results").find(".result[data-result-type=" + field + "]");
        if (result) {
            resultBox.removeClass("test-fail").removeClass("test-loading").addClass("test-success").text(Foris.messages.ok);
        } else {
            resultBox.removeClass("test-success").removeClass("test-loading").addClass("test-fail").text(Foris.messages.error);
        }
    }
    Foris.WS["wan"] = function(msg) {
        switch(msg["action"]) {
            case "connection_test":
                if (msg["data"]["test_id"] != Foris.watched_test) {
                    break;
                }
                for (var key in msg["data"]["data"]) {
                    update_conn_test_field(key, msg["data"]["data"][key]);
                }
                break;
            case "connection_test_finished":
                if (msg["data"]["test_id"] != Foris.watched_test) {
                    break;
                }
                if (!msg["data"]["passed"]) {
                    break;
                }
                for (var key in msg["data"]["data"]) {
                    update_conn_test_field(key, msg["data"]["data"][key]);
                }
                Foris.watched_test = null;
                $("#test-connection").show();
                break;
        }
    }
    $(document).ready(function() {
        $("#test-connection").click(function(e) {
            $("#connection-test-fail").hide();
            var self = $(this);
            e.preventDefault();
            self.attr("disabled", "disabled");
            var ipv6_type = $("select[name='wan6_proto']").val();
            $.get('{{ url("config_ajax", page_name="wan") }}', {action: "check-connection", ipv6_type: ipv6_type})
                    .done(function(response) {
                        $("#test-results").find(".result").removeClass("test-success").removeClass("test-fail").addClass("test-loading").text(Foris.messages.loading);
                        $("#test-connection").hide();
                        Foris.watched_test = response["test_id"];
                    })
                    .fail(function(xhr) {
                        if (xhr.responseJSON && xhr.responseJSON.loggedOut && xhr.responseJSON.loginUrl) {
                            window.location.replace(xhr.responseJSON.loginUrl);
                            return;
                        }
                        $("#connection-test-fail").show();
                    })
                    .always(function() {
                        self.removeAttr("disabled");
                    });
        });
        $('#field-ignore_root_key_1').click(function () {
          if (this.checked)
            return confirm(Foris.messages.confirmDisabledDNSSEC);
          return true;
        });
    });
</script>
