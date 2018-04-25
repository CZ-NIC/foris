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

<div id="page-dns" class="config-page">
     %include("_messages.tpl")
    <p>{{ trans("Router Turris uses its own DNS resolver with DNSSEC support. It is capable of working alone or it can forward your DNS queries through your internet service provider's DNS resolver.") }}</p>
    <p>{{ trans("The following setting determines the behavior of the DNS resolver. It is usually better to use the ISP's resolver in networks where it works properly. In case this does not work for some reason, it is necessary to use direct resolving without forwarding.") }}</p>
    %if not contract_valid():
      <p>{{! trans("In rare cases ISP's have improperly configured network which interferes with DNSSEC validation. If you experience problems with DNS, you can <strong>temporarily</strong> disable DNSSEC validation to determine the source of the problem. However, keep in mind that without DNSSEC validation, you are vulnerable to DNS spoofing attacks! Therefore we <strong>recommend keeping DNSSEC turned on</strong> and resolving the situation with your ISP as this is a serious flaw on their side.") }}</p>
    %end
    <form id="main-form" class="config-form" action="{{ request.fullpath }}" method="post" enctype="multipart/form-data" autocomplete="off" novalidate>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include("_field.tpl", field=field)
        %end
        <div class="form-buttons">
            <a href="{{ request.fullpath }}" class="button grayed">{{ trans("Discard changes") }}</a>
            <button type="submit" name="send" class="button">{{ trans("Save changes") }}</button>
        </div>
    </form>

    <h2>{{ trans("Connection test") }}</h2>
    <p>{{! trans("Here you can test your internet connection. This test is also useful when you need to check that your DNS resolving works as expected. Remember to click on the <strong>Save</strong> button if you changed your forwarder setting.") }}</p>
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
            <tr><td>{{ trans("DNS") }}</td><td class="result" data-result-type="dns-conn-test">???</td></tr>
            <tr><td>{{ trans("DNSSEC") }}</td><td class="result" data-result-type="dnssec-conn-test">???</td></tr>
        </tbody>
    </table>
    <a href="#" id="test-connection" class="button">{{ trans("Test connection") }}</a>
</div>
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
            $.get('{{ url("config_ajax", page_name="dns") }}', {action: "check-connection"})
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
