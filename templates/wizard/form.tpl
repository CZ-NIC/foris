%rebase wizard/base **locals()

<form id="wizard-main-form" class="wizard-form" action="" method="post" autocomplete="off">
    <h1>{{ first_title }}</h1>
    <p class="wizard-description">{{ first_description }}</p>
    %for field in form.active_fields:
        <div>{{! field.label_tag }}{{! field.render() }}</div>
    %end
    <button class="button-next" type="submit" name="send" class="button-arrow-right">{{ _("Next") }}</button>
</form>