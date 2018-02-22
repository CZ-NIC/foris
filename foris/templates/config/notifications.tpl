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

<div id="page-index" class="config-page">
    <p class="config-description">
    {{ trans("Following notifications occured and haven't been dismissed since last reboot.") }}
    </p>

    %if len(notifications):
        %include("_notifications.tpl", notifications=notifications)
    %else:
        <strong>{{ trans("No new messages.") }}</strong>
    %end
</div>
<script>
  $(document).ready(function() {
    $(".notification .reboot").click(function(e) {
      e.preventDefault();
      var unread = $(".notification:visible").length - 1;
      var extraMessage = "";
      if (unread > 0)
        extraMessage = Foris.messages.confirmRestartExtra.replace(/%UNREAD%/g, unread);
      if (confirm(Foris.messages.confirmRestart + extraMessage)) {
        $.get('{{ url("reboot") }}')
          .done(function(response, status, xhr) {
            $("html, body").stop().animate({scrollTop:0}, 500, "swing");
          });
      }
    });
  });
</script>
