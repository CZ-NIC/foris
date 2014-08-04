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
%rebase("_layout.tpl", **locals())

%include("wizard/_header.tpl", can_skip_wizard=False)

<div id="wizard-content">
    <h1>{{ trans("Welcome to configuration of router Turris") }}</h1>

    <p>{{ trans("Before you start to use the router for the first time, it is necessary to set it up. The following simple wizard will take you through the configuration procedure. After it is finished, your router will be ready for operation.") }}</p>
    <hr>
    <p class="footnote">{{ trans("If you want to restore a previously saved configuration or for some other reason skip this wizard, you can do so after choosing a password in its first step.") }}</p>

    <a href="{{ url("wizard_step", number=1) }}" class="button-next" type="submit" name="send" class="button-arrow-right">{{ trans("Begin installation") }}</a>
</div>