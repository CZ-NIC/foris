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
%rebase("wizard/base", **locals())

<div id="wizard-updater">
    <h1>{{ trans(first_title) }}</h1>
    %if DEVICE_CUSTOMIZATION == "omnia":
      <div id="updater-eula">
        %include("includes/updater_eula.tpl")
        <br>
        %include("includes/updater_eula_summary.tpl")

        <form id="eula-form" class="wizard-form wizard-form-eula" action="{{ url("wizard_ajax", number=6) }}?action=submit_eula" method="post" autocomplete="off" novalidate>
            %include("_messages.tpl")
            <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
            <div class="row">
              {{! form.active_fields[0].render() }}
            </div>
            <button class="button-next button-arrow-right" type="submit" name="send">{{ trans("Next") }}</button>
        </form>
      </div>
    %end
    <div id="updater-progress" class="background-progress">
        <img src="{{ static("img/loader.gif") }}" alt="{{ trans("Loading...") }}"><br>
        %if stepnumber == "7":
            {{ trans("Installing additional updates. Router will be restarted several times to finish the process.") }}<br>
            {{ trans("Do not unplug the device during update!") }}<br>
        %else:
            {{ trans("Check of available updates in progress.") }}<br>
        %end
        {{ trans("One moment, please...") }}<br>
        <div id="wizard-updater-status"></div>
    </div>
    <div id="updater-success">
        <img src="{{ static("img/success.png") }}" alt="{{ trans("Done") }}"><br>
        <p>{{ trans("Firmware update was successful, you can proceed to the next step.") }}</p>
        <a class="button-next" href="{{ next_step_url }}">{{ trans("Next") }}</a>
    </div>
    <div id="updater-fail">
        <img src="{{ static("img/fail.png") }}" alt="{{ trans("Error") }}"><br>
        <p>
            {{ trans("Firmware update has failed due to a connection or installation error. You should check your cable connection before proceeding to the next step. But do not worry much about the update as the router will run the updater regularly.") }}
        </p>
        <div id="updater-fail-message">
          {{ trans("Updater has returned the following error:") }}
          <pre></pre>
        </div>
        <a class="button-next" href="{{ next_step_url }}">{{ trans("Next") }}</a>
    </div>
    <div id="updater-login">
        <img src="{{ static("img/success.png") }}" alt="{{ trans("Done") }}"><br>
        <p>{{ trans("Device has been restarted.") }}<br>
        {{ trans("Please log in again to continue.") }}</p>
        <a class="button" href="{{ url("index") }}?next={{ url("wizard_step", number=stepnumber) }}">{{ trans("Proceed to login") }}</a>
    </div>
</div>

<script>
    $(document).ready(function() {
    %if stepnumber == "7":
        Foris.checkUpdaterStatus(null, {{ stepnumber }});
    %elif DEVICE_CUSTOMIZATION == "omnia":
        Foris.initEulaForm();
    %else:
      Foris.runUpdater();
    %end
    });
</script>
