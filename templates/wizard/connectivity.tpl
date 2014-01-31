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

<div id="wizard-connectivity">
    <h1>{{ first_title }}</h1>
    <div id="connectivity-progress" class="background-progress">
        <img src="{{ static("img/loader.gif") }}" alt="{{ trans("Loading...") }}"><br>
        <div id="wizard-connectivity-status">
          <p>
            {{ trans("Checking internet connectivity.") }}<br>
            {{ trans("One moment, please...") }}
          </p>
        </div>
    </div>
    <div id="connectivity-success">
        <img src="{{ static("img/success.png") }}" alt="{{ trans("Done") }}"><br>
        <p>{{ trans("Your network settings are alright.") }}</p>
        <a class="button-next" href="{{ url("wizard_step", number=5) }}">{{ trans("Next") }}</a>
    </div>
    <div id="connectivity-nodns">
        <img src="{{ static("img/fail.png") }}" alt="{{ trans("Error") }}"><br>
        <p>
            {{ trans("Your internet connection has network connectivity but DNS resolving does not work. This is probably a problem with your ISP.") }}
        </p>
        <a class="button-next" href="{{ url("wizard_step", number=5) }}">{{ trans("Next") }}</a>
    </div>
    <div id="connectivity-fail">
        <img src="{{ static("img/fail.png") }}" alt="{{ trans("Error") }}"><br>
        <p>
            {{! trans("It seems that you have no internet connection. Maybe your WAN settings are not right. If you wish, you can <a href=\"%(link)s\">check them once again</a>.") % dict(link=url("wizard_step", number=2)) }}
        </p>
        <a class="button-next" href="{{ next_step_url }}">{{ trans("Next") }}</a>
    </div>
</div>

<script>
    $(document).ready(function() {
        ForisWizard.connectivityCheck();
    });
</script>