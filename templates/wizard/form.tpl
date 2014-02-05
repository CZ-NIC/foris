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

<form id="main-form" class="wizard-form" action="{{ request.fullpath }}" method="post" autocomplete="off" novalidate>
    <h1>{{ trans(first_title) }}</h1>
    <p class="wizard-description">{{! first_description }}</p>
    %include _messages
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
    %for field in form.active_fields:
        %include _field field=field
    %end
    <button class="button-next button-arrow-right" type="submit" name="send">{{ trans("Next") }}</button>
</form>
