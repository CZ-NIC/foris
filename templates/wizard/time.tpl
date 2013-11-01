%rebase wizard/base **locals()

%if form:
    <form class="wizard-form" action="" method="post">
        <h1>{{ first_title }}</h1>
        <p>{{ first_description }}</p>
        <div class="form-fields">
        %for field in form.active_fields:
            <div>{{! field.label_tag }}{{! field.render() }}</div>
        %end
        </div>

        <div id="wizard-time-sync">
            <a href="#" id="wizard-time-sync-auto" class="button">{{ _("Synchronize with computer clock") }}</a>
            <a href="#" id="wizard-time-sync-manual" class="button">{{ _("Set time manually") }}</a>
            <p id="wizard-time-sync-success">{{ _("Synchronization successful.") }}</p>
        </div>

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