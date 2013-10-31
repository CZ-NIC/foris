%rebase wizard/base **locals()

%if form:
    <form class="wizard-form" action="" method="post">
        <h1>{{ first_title }}</h1>
        <p>{{ first_description }}</p>
        %for field in form.active_fields:
            <div>{{! field.label_tag }}{{! field.render() }}</div>
        %end
        <button class="button-next" type="submit" name="send" class="button-arrow-right">{{ _("Next") }}</button>
    </form>
%else:
    <div id="wizard-time">
        <h1>{{ _("Time settings") }}</h1>
        <div id="time-progress" class="background-progress">
            <img src="/static/img/loader.gif" alt="{{ _("Loading...") }}"><br>
            {{ _("Synchronizing with time in the internet.") }}<br>
            {{ _("Please wait...")  }}
        </div>

        <div id="time-success">
            <img src="/static/img/success.png" alt="{{ _("Done") }}"><br>
            <p>{{ _("Time was successfully synchronized, you can move to the next step.") }}</p>
            <a class="button-next" href="/wizard/step/4">{{ _("Next") }}</a>
        </div>
    </div>

    <script>
        $(document).ready(function(){
            ForisWizard.ntpUpdate();
        });
    </script>
%end