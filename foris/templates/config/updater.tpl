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
%rebase("config/base.tpl", **locals())

%if not defined('is_xhr'):
<div id="page-config" class="config-page">
%end
    %include("_messages.tpl")

    <p>{{! description }}</p>

    %if defined('auto_updates_form'):
      %if collecting_enabled:
        <div class="message info">{{ trans("Data collection is currently enabled. You can not disable updater without disabling the data collection first.") }}</div>
      %else:
          %include("includes/updater_eula.tpl")

          <form id="updater-auto-updates-form" class="maintenance-form" action="{{ url("config_action", page_name="updater", action="toggle_updater") }}" method="post" autocomplete="off" novalidate>
              %include("_messages.tpl")
              <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
              <div class="row">
                {{! auto_updates_form.active_fields[0].render() }}
              </div>

        %if auto_updates_form.active_fields[0].field.value == "1":
        <h4>{{ trans("Update approvals") }}</h4>
        <div id="updater-approvals">
        %for field in auto_updates_form.sections[1].active_fields:
            <div>
            %if field.name == "approval_timeout":
              <div id="approval-timeout-line">
              <label for="{{ field.field.id }}">
              {{! trans("after %(input)s hours") % dict(input=field.render()) }}
              </label>
              </div>
            %else:
              <label for="{{ field.field.id }}">
              {{! field.render() }}
              {{ field.field.description }}
              </label>
            %end
            %if field.hint:
              <img class="field-hint" src="{{ static("img/icon-help.png") }}" title="{{ field.hint }}" alt="{{ trans("Hint") }}: {{ field.hint }}">
            %end
            %if field.errors:
              <div class="server-validation-container">
                <ul>
                  <li>{{ field.errors }}</li>
                </ul>
              </div>
            %end
            </div>
        %end
        %end
        </div>
            <div class="row">
              <button type="submit" name="send" class="button">{{ trans("Save") }}</button>
            </div>
          </form>
      %end
    %end

    %if defined('updater_disabled') and updater_disabled:
      <div class="message warning">
        {{ trans("The Updater is currently disabled. You must enable it first to manage package lists.") }}
      </div>
    %else:
      <h2>{{ trans("Package lists") }}</h2>
      <form id="main-form" class="config-form" action="{{ url("config_page", page_name="updater") }}" method="post" autocomplete="off" novalidate>

          <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">
          %for field in form.sections[0].sections[0].active_fields:
              %if field.hidden:
                  {{! field.render() }}
              %else:
              <div class="row">
                  {{! field.render() }}
                  {{! field.label_tag[lang()] }}
                  {{ field.hint[lang()] }}
                  %if field.errors:
                    <div class="server-validation-container">
                      <ul>
                        <li>{{ field.errors }}</li>
                      </ul>
                    </div>
                  %end
              </div>
              %end
          %end
          <div id="language-install">
          <h5>{{ form.sections[0].sections[1].title }}</h5>
          %for field in form.sections[0].sections[1].active_fields:
            <div class="language-install-box">{{! field.render() }} {{! field.label_tag }}</div>
          %end
          </div>
          %if len(form.sections[0].sections[0].active_fields) == 0:
            <div class="message warning">
              {{ trans("List of available software was not downloaded from the server yet. Please come back later.") }}
            </div>
          %else:
            <div class="form-buttons">
                <a href="{{ request.fullpath }}" class="button grayed">{{ trans("Discard changes") }}</a>
                <button type="submit" name="send" class="button">{{ trans("Save changes") }}</button>
            </div>
          %end
      </form>
    %end
%if not defined('is_xhr'):
</div>
<script>
  $('#field-agreed_0').click(function () {
    return confirm(Foris.messages.confirmDisabledUpdates);
  });
</script>
%end
