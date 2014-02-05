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

<div id="page-dns" class="config-page">
    <h2>{{ trans("DNS setup") }}</h2>
     %include _messages
    <p>{{ trans("Router Turris uses its own DNS resolver with DNSSEC support. It is capable of working alone or it can forward your DNS queries through your internet service provider's DNS resolver.") }}</p>
    <p>{{ trans("The following setting determines the behavior of the DNS resolver. It is usually better to use the ISP's resolver in networks where it works properly. In case this does not work for some reason, it is necessary to use direct resolving without forwarding.") }}</p>
    <form id="main-form" class="dns-form" action="{{ request.fullpath }}" method="post" enctype="multipart/form-data" autocomplete="off" novalidate>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include _field field=field
        %end
        <button type="submit" name="send" class="button">{{ trans("Save") }}</button>
    </form>

    <h3>{{ trans("Connection test") }}</h3>
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
            <tr><td>{{ trans("IPv4 connectivity") }}</td><td class="result" data-result-type="IPv4-connectivity">???</td></tr>
            <tr><td>{{ trans("IPv4 gateway connectivity") }}</td><td class="result" data-result-type="IPv4-gateway">???</td></tr>
            <tr><td>{{ trans("IPv6 connectivity") }}</td><td class="result" data-result-type="IPv6-connectivity">???</td></tr>
            <tr><td>{{ trans("IPv6 gateway connectivity") }}</td><td class="result" data-result-type="IPv6-gateway">???</td></tr>
            <tr><td>{{ trans("DNS") }}</td><td class="result" data-result-type="DNS">???</td></tr>
            <tr><td>{{ trans("DNSSEC") }}</td><td class="result" data-result-type="DNSSEC">???</td></tr>
        </tbody>
    </table>
    <a href="#" id="test-connection" class="button">{{ trans("Test connection") }}</a>
</div>
<script>
    $(document).ready(function() {
        $("#test-connection").click(function(e) {
            $("#connection-test-fail").hide();
            var self = $(this);
            e.preventDefault();
            self.attr("disabled", "disabled");
            self.after('<img src="/static/img/icon-loading.gif" id="connection-test-loader" alt="' + Foris.messages.loading + '">');
            $.get("/config/dns/ajax", {action: "check-connection"})
                    .done(function(response) {
                        if (response.success) {
                            for (var key in response.check_results) {
                              if (response.check_results.hasOwnProperty(key)) {
                                var resultBox = $("#test-results").find(".result[data-result-type=" + key + "]");
                                if (resultBox) {
                                    if (response.check_results[key])
                                        resultBox.removeClass("test-fail").addClass("test-success").text(Foris.messages.ok);
                                    else
                                        resultBox.removeClass("test-success").addClass("test-fail").text(Foris.messages.error);
                                }
                              }
                            }
                        }
                        else {
                          $("#connection-test-fail").show();
                        }
                    })
                    .fail(function() {
                        $("#connection-test-fail").show();
                    })
                    .always(function() {
                        $("#connection-test-loader").remove();
                        self.removeAttr("disabled");
                    });
        });
    });
</script>