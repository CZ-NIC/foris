%rebase wizard/base **locals()

<form id="wizard-form" action="" method="post">
    <h1>{{ first_title }}</h1>
    <p>{{ first_description }}</p>
    %for field in form.active_fields:
        <div>{{! field.label_tag }}{{! field.render() }}</div>
    %end
    <input type="submit" name="send" value="Send">
</form>