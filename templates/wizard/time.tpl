%rebase wizard/base **locals()

%if form:
    <form class="wizard-form" action="{{ request.fullpath }}" method="post">
        <h1>{{ first_title }}</h1>
        <p>{{ first_description }}</p>
        <div class="form-fields">
        %for field in form.active_fields:
            %if field.hidden:
                {{! field.render() }}
            %else:
            <div>
                {{! field.label_tag }}
                {{! field.render() }}
                %if field.hint:
                    <img class="field-hint" src="{{ static("img/icon-help.png") }}" title="{{ field.hint }}">
                %end
            </div>
            %end
        %end
        </div>

        <div id="wizard-time-sync">
            <a href="#" id="wizard-time-sync-auto" class="button">{{ _("Synchronize with your computer clock") }}</a>
            <a href="#" id="wizard-time-sync-manual" class="button">{{ _("Set time manually") }}</a>
            <p id="wizard-time-sync-success">{{ _("Synchronization successful.") }}</p>
        </div>

        <button class="button-next" type="submit" name="send" class="button-arrow-right">{{ _("Next") }}</button>
    </form>
%else:
    <div id="wizard-time">
        <h1>{{ _("Time settings") }}</h1>
        <div id="time-progress" class="background-progress">
            <img src="{{ static("img/loader.gif") }}" alt="{{ _("Loading...") }}"><br>
            {{ _("Synchronizing router time with a timeserver.") }}<br>
            {{ _("One moment, please...")  }}
        </div>

        <div id="time-success">
            <img src="{{ static("img/success.png") }}" alt="{{ _("Done") }}"><br>
            <p>{{ _("Time was successfully synchronized, you can move to the next step.") }}</p>
            <a class="button-next" href="{{ url("wizard_step", number=4) }}">{{ _("Next") }}</a>
        </div>
    </div>

    <script>
        $(document).ready(function(){
            ForisWizard.ntpUpdate();
        });
    </script>
%end