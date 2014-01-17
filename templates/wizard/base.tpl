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
%if not defined('is_xhr'):
    %rebase _layout **locals()

    <div id="wizard-header">
        <img src="{{ static("/img/logo-turris.png") }}" alt="{{ trans("Project:Turris") }}">
        <div class="wizard-steps">
        %if can_skip_wizard:
            <a href="{{ url("wizard_skip") }}">{{ trans("Skip wizard") }}</a>
        %end
            <br>
            <span class="stepno"><span class="stepno-current">{{ stepnumber }}</span> / 7</span>
        </div>
    </div>

%if stepname:
    <div id="wizard-icon"><img src="{{ static("img/wizard/step-%s.png", stepname) }}" alt="{{ trans("Step") }} {{ stepnumber }}"></div>
%end
    <div id="wizard-content">
%end

    %include

%if not defined('is_xhr'):
    </div>
%end