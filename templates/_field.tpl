%if field.hidden:
    {{! field.render() }}
%else:
<div class="row">
    {{! field.label_tag }}
    {{! field.render() }}
    %if field.hint:
        <img class="field-hint" src="{{ static("img/icon-help.png") }}" title="{{ field.hint }}" alt="{{ _("Hint") }}: {{ field.hint }}">
    %end
    %if field.field.note:
      <div class="server-validation-container">
        <ul>
          <li>{{ field.field.note }}</li>
        </ul>
      </div>
    %end
</div>
%end