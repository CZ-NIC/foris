%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2015 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

<div id="page-maintenance" class="config-page">
  %if DEVICE_CUSTOMIZATION == "omnia":
    <!-- todo: translate -->
    <p>S routerem Turris Omnia je možné zapojit se do projektu TURRIS, což je neziskový výzkumný projekt sdružení CZ.NIC, z. s. p. o., správce české národní domény .cz. Tím se stane Váš nový router současně soundou, která analyzuje provoz mezi internetem a domácí sítí a pomáhá identifikovat podezřelé datové toky. Při jejich detekci pak upozorní centrálu TURRIS na možný útok. Centrála systému umožňuje porovnat data z mnoha připojených routerů TURRIS a vyhodnotit nebezpečnost detekovaného provozu. V případě, že je útok odhalen, jsou vytvořeny aktualizace, které jsou distribuovány do celé sítě TURRIS a pomáhají tak chránit její uživatele.</p>

    %if updater_disabled:
      <div class="message warning">
        {{ trans("The Updater is currently disabled. You must enable it first to enable data collection.") }}
      </div>
    %end


    %if defined('registration_check_form'):
      <p>Chcete-li plně využívat výhod tohoto projektu, je nutné se nejprve zaregistrovat na portálu Turris. Zde zadejte Vaši emailovou adresu, kterou si chcete zaregistrovat nebo jste v minulosti pro registraci použil(a):</p>
      <form id="restore-form" class="maintenance-form" action="{{ url("config_action", page_name="data-collection", action="check_registration") }}" method="post" novalidate>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in registration_check_form.active_fields:
            %include("_field.tpl", field=field)
        %end
        <button class="button" name="send" type="submit">{{ trans("Validate email") }}</button>
      </form>
    %end

    %include("_messages.tpl")

    %if defined('collection_toggle_form'):
      %# Terms have been accepted and user can toggle data collection
      <form id="collecting-form" class="maintenance-form" action="{{ url("config_action", page_name="data-collection", action="toggle_collecting") }}" method="post" novalidate>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in collection_toggle_form.active_fields:
            %include("_field.tpl", field=field)
        %end
        <button class="button" name="send" type="submit">{{ trans("Save") }}</button>
      </form>
    %end
  %else:
    %include("_messages.tpl")
  %end

  %if DEVICE_CUSTOMIZATION == "turris" or (defined('agreed') and agreed):
    <h2>{{ form.sections[0].title }}</h2>

    <form id="ucollect-form" class="config-form" action="{{ request.fullpath }}" method="post" autocomplete="off" novalidate>
        <p class="config-description">{{! form.sections[0].description }}</p>
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
        %for field in form.active_fields:
            %include("_field.tpl", field=field)
        %end
        <div class="form-buttons">
            <a href="{{ request.fullpath }}" class="button grayed">{{ trans("Discard changes") }}</a>
            <button type="submit" name="send" class="button">{{ trans("Save changes") }}</button>
        </div>
    </form>
  %end
</div>
