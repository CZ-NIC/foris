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

<div id="page-about">
    <h2>{{ trans("About") }}</h2>
        %include _messages
        <table>
            <tbody>
                <tr>
                    <th>{{ trans("Device") }}</th>
                    <td>{{ trans("Router Turris - model RTRS01") }}</td>
                </tr>
                <tr>
                    <th>{{ trans("Serial number") }}</th>
                    <td>{{ serial.decimal }}</td>
                </tr>
                <tr>
                    <th>{{ trans("Kernel version") }}</th>
                    <td>{{ stats['kernel-version'] }}</td>
                </tr>
            </tbody>
        </table>

    <h2>{{ trans("Device registration") }}</h2>
    <div class="about-description">
        <p>
            {{! trans("If you did not register your device before, click on the following button to obtain a registration code. This code must be submitted on the Turris site in your user profile available at: <a href=\"%(url)s\">%(url)s</a>.") % {'url': "https://www.turris.cz/user/register-router"} }}
        </p>
        <p>
            {{ trans("Registration code") }}: <span id="registration-code">????????</span>
        </p>
        <div id="registration-code-fail">
            <p>
                {{ trans("Unfortunately, it wasn't possible to generate the registration code. This usually means the router is not connected to the internet. Please, try registering later. If the problem persists, contact the support.") }}
            </p>
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
            self.after('<img src="/static/img/icon-loading.gif" id="registration-code-loader" alt="Loading...">');
            $.get("/config/about/ajax", {action: "registration_code"})
                    .done(function(response) {
                        if (response.success) {
                            $("#registration-code").text(response.data).show();
                            $("#registration-code-fail").hide();
                        }
                        else {
                            $("#registration-code").text("????????");
                            $("#registration-code-fail").show();
                        }
                    })
                    .fail(function() {
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
