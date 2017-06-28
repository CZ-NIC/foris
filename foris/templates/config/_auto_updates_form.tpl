%if collecting_enabled:
  <div class="message info">{{ trans("Data collection is currently enabled. You can not disable updater without disabling the data collection first.") }}</div>
%else:
  %include("includes/updater_eula.tpl")
%end

<form id="updater-auto-updates-form" class="maintenance-form" action="{{ url("config_action", page_name="updater", action="toggle_updater") }}" method="post" autocomplete="off" novalidate>
  %include("_messages.tpl")
  <input type="hidden" name="csrf_token" value="{{ get_csrf_token() }}" />

%if not collecting_enabled:
  <div class="row">
    {{! form.active_fields[0].render() }}
  </div>
%end

%if collecting_enabled or form.active_fields[0].field.value == "1":
  <h4>{{ trans("Update approvals") }}</h4>
  <div id="updater-approvals">
  %if DEVICE_CUSTOMIZATION == "turris":
    <p>{{! trans("Update approvals can be handy in case you want to be sure that updates will not harm some of your very special configurations. You can postpone the questionable update temporarily and install them when you are prepared. It is not possible to deny the update forever, it will be proposed to you together with the next update again.") }}</p>
  %else:
    <p>{{! trans("Update approvals can be handy in case you want to be sure that updates will not harm some of your very special configurations. You can e.g. install updates when you are prepared for a possible <a href='https://www.turris.cz/doc/en/howto/omnia_factory_reset#rollback_to_latest_snapshot'>rollback to the previous snapshot</a> and postpone the questionable update temporarily. It is not possible to deny the update forever, it will be proposed to you together with the next update again." ) }}</p>
  %end
  %for field in form.sections[1].active_fields:
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
  </div>
%end

  <div class="row">
    <button type="submit" name="send" class="button">{{ trans("Save") }}</button>
  </div>
</form>
