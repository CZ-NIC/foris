%if field.hidden:
    {{! field.render() }}
%else:
<div class="row">
    {{! field.label_tag }}
    {{! field.render() }}
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