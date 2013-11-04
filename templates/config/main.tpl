%rebase config/base **locals()

<form id="wizard-main-form" class="wizard-form" action="" method="post" autocomplete="off">
    <h1>{{ title }}</h1>
    <p class="wizard-description">{{ description }}</p>
    %for field in form.active_fields:
        <div>
            {{! field.label_tag }}
            {{! field.render() }}
            %if field.hint:
                <img class="field-hint" src="/static/img/icon-help.png" title="{{ field.hint }}">
            %end
        </div>
    %end
    <button type="submit" name="send" class="button">{{ _("Save") }}</button>
</form>