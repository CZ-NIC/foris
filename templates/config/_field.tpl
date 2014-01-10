%if field.hidden:
    {{! field.render() }}
%else:
<div>
    {{! field.label_tag }}
    {{! field.render() }}
    %if field.hint:
        <img class="field-hint" src="{{ static("img/icon-help.png") }}" title="{{ field.hint }}" alt="{{ _("Hint") }}: {{ field.hint }}">
    %end
    %if field.field.note:
        <div class="field-validation-fail">{{ field.field.note }}</div>
    %end
</div>
%end