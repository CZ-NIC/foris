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

<div id="wizard-updater">
    <h1>{{ first_title }}</h1>
    <div id="updater-progress" class="background-progress">
        <img src="{{ static("img/loader.gif") }}" alt="{{ trans("Loading...") }}"><br>
        {{ trans("Check of available updates in progress.") }}<br>
        {{ trans("One moment, please...") }}<br>
        <div id="wizard-updater-status"></div>
    </div>
    <div id="updater-success">
        <img src="{{ static("img/success.png") }}" alt="{{ trans("Done") }}"><br>
        <p>{{ trans("Firmware update has succeeded, you can proceed to next step.") }}</p>
        <a class="button-next" href="{{ next_step_url }}">{{ trans("Next") }}</a>
    </div>
    <div id="updater-fail">
        <img src="{{ static("img/fail.png") }}" alt="{{ trans("Error") }}"><br>
        <p>
            {{ trans("Firmware update has failed due to a connection or an installation error. You should check your cable connection before proceeding to the next step. But do not worry much about the update as the router will run the updater regularly.") }}
        </p>
        <a class="button-next" href="{{ next_step_url }}">{{ trans("Next") }}</a>
    </div>
</div>

<script>
    $(document).ready(function() {
        ForisWizard.runUpdater();
    });
</script>