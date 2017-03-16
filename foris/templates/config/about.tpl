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

<div id="page-about" class="config-page">
    %include("_messages.tpl")
    <table>
        <tbody>
            <tr>
                <th>{{ trans("Device") }}</th>
                <td>{{ stats['model'] }} - {{ stats['board-name'] }}</td>
            </tr>
            <tr>
                <th>{{ trans("Serial number") }}</th>
                <td>{{ serial.decimal }}</td>
            </tr>
            <tr>
                <th>{{ trans("Turris OS version") }}</th>
                <td>{{ stats['turris-os-version'] }}</td>
            </tr>
            <tr>
                <th>{{ trans("Kernel version") }}</th>
                <td>{{ stats['kernel-version'] }}</td>
            </tr>
          %if contract_valid() or agreed_collect:
            <tr>
                <th>{{ trans("Sending of uCollect data") }}</th>
                <td class="{{ "sending-ok" if stats['sending']['ucollect']['alive'] else "sending-fail" }}">
                  {{ translate_sending_status(stats['sending']['ucollect']['status']) }}
                  % if stats['sending']['ucollect'].get('age') is not None:
                      <abbr title="{{! trans("Time of last update: %(datetime)s") % dict(datetime=stats['sending']['ucollect']['last_update'].strftime(trans("%Y/%m/%d %H:%M:%S"))) }}">
                        {{ ungettext("(status updated %d second ago)", "(status updated %d seconds ago)", stats['sending']['ucollect']['age']) % stats['sending']['ucollect']['age'] }}
                      </abbr>
                  % end
                </td>
            </tr>
            <tr>
                <th>{{ trans("Sending of firewall logs") }}</th>
                <td class="{{ "sending-ok" if stats['sending']['firewall']['alive'] else "sending-fail" }}">
                  {{ translate_sending_status(stats['sending']['firewall']['status']) }}
                  % if stats['sending']['firewall'].get('age') is not None:
                      <abbr title="{{! trans("Time of last update: %(datetime)s") % dict(datetime=stats['sending']['firewall']['last_update'].strftime(trans("%Y/%m/%d %H:%M:%S"))) }}">
                        {{ ungettext("(status updated %d second ago)", "(status updated %d seconds ago)", stats['sending']['firewall']['age']) % stats['sending']['firewall']['age'] }}
                      </abbr>
                  % end
                </td>
            </tr>
            <tr>
                <th></th>
                <td>
                  <a href="{{ url("config_page", page_name="about") }}" class="reload">{{ trans("Refresh") }}</a>
                </td>
            </tr>
          %end
        </tbody>
    </table>

%if not contract_valid():
</div>
%else:
    <h2>{{ trans("Device registration") }}</h2>
    <div class="about-description">
        <p>
            {{! trans("If you have not registered your device yet, click on the following button to obtain a registration code. This code must be submitted on the Turris site in your user profile available at: <a href=\"%(url)s\">%(url)s</a>.") % {'url': "https://www.turris.cz/user/register-router"} }}
        </p>
        <p>
            {{ trans("Registration code") }}: <span id="registration-code">????????</span>
        </p>
        <div id="registration-code-fail">
            {{ trans("Unfortunately, it wasn't possible to generate the registration code. This usually means the router is not connected to the internet. Please, try registering later. If the problem persists, contact the support.") }}
        </div>
        <button id="registration-code-update" class="button">{{ trans("Get registration code") }}</button>
    </div>
</div>
<script>
    $(document).ready(function() {
        $("#registration-code-update").click(function(e) {
            var self = $(this);
            e.preventDefault();
            self.attr("disabled", "disabled");
            self.after('<img src="{{ static("img/icon-loading.gif") }}" id="registration-code-loader" alt="' + Foris.messages.loading +'">');
            $.get('{{ url("config_ajax", page_name="about") }}', {action: "registration_code"})
                    .done(function(response, status, xhr) {
                        if (response.success) {
                            $("#registration-code").text(response.data).show();
                            $("#registration-code-fail").hide();
                        }
                        else {
                            $("#registration-code").text("????????");
                            $("#registration-code-fail").show();
                        }
                    })
                    .fail(function(xhr) {
                        if (xhr.responseJSON && xhr.responseJSON.loggedOut && xhr.responseJSON.loginUrl) {
                            window.location.replace(xhr.responseJSON.loginUrl);
                            return;
                        }
                        $("#registration-code").text("????????");
                        $("#registration-code-fail").show();
                    })
                    .always(function() {
                        $("#registration-code-loader").remove();
                        self.removeAttr("disabled");
                    });
        });
    });
</script>
%end
