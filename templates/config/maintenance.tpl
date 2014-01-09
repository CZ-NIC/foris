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

<div id="page-maintenance">
    <h2>{{ _("Maintenance") }}</h2>
    <div class="maintenance-description">
        <!-- TODO: reversing does not work yet <a href="{{ url("config_page", page_name="maintenance", action="config-backup") }}" class="button">{{ _("Download configuration backup") }}</a -->
        <a href="/config/maintenance/action/config-backup" class="button">{{ _("Download configuration backup") }}</a>
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
