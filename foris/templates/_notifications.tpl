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
<div id="notifications-content">
%if len(notifications):
  <div id="notifications-list">
%for notification in notifications:
    <div class="notification {{ notification["severity"] }}" id="notification_{{ notification["id"]  }}">
      <h2>{{! helpers.make_notification_title(notification) }}</h2>
      {{! helpers.transform_notification_message(notification["msg"]) }}
      %if notification["severity"] == "restart":
        <div class="buttons">
            <a href="{{ url("reboot") }}" class="button reboot">{{ trans("Reboot now") }}</a>
        </div>
      %else:
        <a href="#" class="dismiss" title="{{ trans("Dismiss") }}" data-id="{{ notification["id"] }}">&times;</a>
      %end
    </div>
%end
  </div>
  <div class="row" style="{{ "" if [e for e in notifications if not e["severity"] == "restart"] else "display: none" }}">
    <button type="submit" class="button" id="dismiss-all-notifications">{{ trans("Dismiss All") }}</button>
  </div>
%else:
        <strong>{{ trans("No new messages.") }}</strong>
%end
</div>
