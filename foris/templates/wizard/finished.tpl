%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2016 CZ.NIC, z.s.p.o. <https://www.nic.cz>
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
%# along with this program.  If not, see <https://www.gnu.org/licenses/>.
%#
%rebase("wizard/base", **locals())

<h1>{{ trans("Installation finished") }}</h1>

<p>{{! trans("You can change any of the previously configured settings in the <a href=\"%(url)s\">standard configuration interface</a>. In case you are interested in more advanced options, you can use the LuCI interface which is available from the <a href=\"%(url2)s\">Advanced administration tab</a>.") % {'url': "TODO", 'url2': "TODO"} }}</p>

<h2>{{ trans("What next?") }}</h2>

%if not agreed_updater:
  <p>
    {{ trans("You have decided to disable the Updater service during the installation.") }}
    {{ trans("Without the Updater, installed software will not be kept up to date and you will also not be able to install Updater's package lists.") }}
    {{! trans('By enabling of the Updater, you can also join our research project: <a href="https://www.turris.cz/">Project Turris</a>.') }}
  </p>
  <p>{{! trans('You can enable the Updater any time on the <a href=\"%(url)s\">Updater</a> configuration page.') % dict(url="TODO") }}</p>
%else:
  <p>{{! trans('With Turris Omnia you can join the research project called <a href="https://www.turris.cz/">Project Turris</a>. Thanks to this project, your router can become a probe that analyzes the traffic between internet and the home network and identifies suspicious data flows.') }}</p>
  <p>{{! trans('You can enable these additional features by following the instructions on the <a href="%(url)s">Data collection</a> page.') % dict(url="TODO") }}</p>
%end

%if len(notifications):
    <h2>{{ trans("Important updates") }}</h2>
    <p>{{ trans("Important updates that require a device restart have been installed. Some services might not work if you don't restart the device. For details see below.")  }}</p>
    %include("_notifications.tpl", notifications=notifications)
%end

<a class="button-next" href="{{ "TODO" }}">{{ trans("Continue to the configuration interface") }}</a>
