%# Foris
%# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

  <p>{{! form.sections[0].description }}</p>
%if agreed_collect and not contract_valid:
    <div class="message info">{{ trans("Data collection is currently enabled. You can not disable updater without disabling the data collection first.") }}</div>
%elif not contract_valid:
    %include("includes/updater_eula.tpl")
%end

  <form id="main-form" class="config-form" action="{{ url("config_page", page_name="updater") }}" method="post" autocomplete="off" novalidate>
    <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}">

%# main updater switch
%if not agreed_collect and not contract_valid:
    <div class="row" id="updater-toggle">
      {{! form.sections[0].active_fields[0].render() }}
    </div>
%end

%# approval settings
%if is_updater_enabled() and not contract_valid:
  <h4>{{ trans("Update approvals") }}</h4>
  <div id="updater-approvals">
  %if foris_info.device_customization == "turris":
    <p>{{! trans("Update approvals can be useful when you want to make sure that updates won't harm your specific configuration. You can refuse the questionable update temporarily and install it when you are ready. It isn't possible to decline the update forever and it will be offered to you again together with the next package installation.") }}</p>
  %else:
    <p>{{! trans("Update approvals can be useful when you want to make sure that updates won't harm your specific configuration. You can e.g. install updates when you're prepared for a possible rollback to a previous snapshot and deny the questionable update temporarily. It isn't possible to decline the update forever and it will be offered to you again together with the next package installation.") }}</p>
  %end
  %for field in form.sections[0].sections[0].active_fields:
    <div class="row">
    %if field.name == "approval_delay":
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
      <img class="field-hint" src="{{ static("img/icon-help.png") }}" title="{{ helpers.remove_html_tags(field.hint) }}" alt="{{ trans("Hint") }}: {{ helpers.remove_html_tags(field.hint) }}">
      <div class="hint-text" style="display: none">{{! field.hint }}</div>
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
  </div>
  %# current approval
  %if get_approval_setting_status() in ["on", "delayed"] and current_approval["present"] and current_approval["status"] in ["asked", "denied"]:
  <div id="current-approval">
    <h4>{{ trans("Approve update from %(when)s") % dict(when=current_approval["time"].strftime("%Y-%m-%d %H:%M:%S")) }}</h4>
    %# render hidden field with approval id
    {{! form.sections[0].sections[3].active_fields[0].render() }}
    <h5>List of changes</h5>
    <ul id="updater-approve-changes">
    %for record in current_approval["plan"]:
    <li class="tooltip" title="{{ helpers.prepare_approval_item_message(record, False) }}">
      {{ helpers.shorten_text(helpers.prepare_approval_item_message(record), 40) }}
    </li>
    %end
    </ul>
    %if current_approval["reboot"]:
    <div id="updater-reboot-text">
      <strong>{{ trans("Note that a reboot will be triggered after the update.") }}</strong>
    </div>
    %end
    <div class="row button-row">
      <button type="submit" name="target" class="button" value="grant">{{ trans("Install now") }}</button>
    %if current_approval["status"] == "asked":
      <button type="submit" name="target" class="button" value="deny">{{ trans("Deny") }}</button>
    %end
    </div>
    %if current_approval["status"] == "denied":
    <p>{{ trans("No package will be installed unless you install the updates above.") }}</p>
    %end
    %if current_approval["status"] == "asked" and get_approval_setting_status() == "delayed":
    <p>{{ trans("If you don't install the updates manually, they will be installed automatically after %(time)s.") % dict(time=helpers.increase_time(current_approval["time"], get_approval_setting_delay()).strftime("%Y-%m-%d %H:%M:%S")) }}</p>
    %end
  </div>
  %end
%end

%if is_updater_enabled() or contract_valid:
  <h2>{{ trans("Package lists") }}</h2>
  %for field in form.sections[0].sections[1].active_fields:
  <div class="row">
    {{! field.render() }}
    {{! field.label_tag }}
    {{ field.hint }}
  </div>
  %end
  <div id="language-install">
  <h5>{{ form.sections[0].sections[2].title }}</h5>
  %for field in form.sections[0].sections[2].active_fields:
    <div class="language-install-box">{{! field.render() }} {{! field.label_tag }}</div>
  %end
  </div>
%end
    <div class="form-buttons">
      <a href="{{ request.fullpath }}" class="button grayed">{{ trans("Discard changes") }}</a>
      <button type="submit" name="target" class="button" value="save">{{ trans("Save changes") }}</button>
    </div>

  </form>


%if not defined('is_xhr'):
</div>
<script>
  $('#field-enabled_0').click(function () {
    return confirm(Foris.messages.confirmDisabledUpdates);
  });
</script>
%end
