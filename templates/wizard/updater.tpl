%rebase wizard/base **locals()

<div id="wizard-updater">
    <h1>{{ _("Connection test and check for new updates.") }}</h1>
    <div id="updater-progress" class="background-progress">
        <img src="{{ static("img/loader.gif") }}" alt="{{ _("Loading...") }}"><br>
        {{ _("Check of available updates in progress.") }}<br>
        {{ _("One moment, please...") }}<br>
        <div id="wizard-updater-status"></div>
    </div>
    <div id="updater-success">
        <img src="{{ static("img/success.png") }}" alt="{{ _("Done") }}"><br>
        <p>{{ _("Firmware update has succeeded, you can proceed to next step.") }}</p>
        <a class="button-next" href="{{ url("wizard_step", number=5) }}">{{ _("Next") }}</a>
    </div>
    <div id="updater-fail">
        <img src="{{ static("img/fail.png") }}" alt="{{ _("Error") }}"><br>
        <p>
            {{ _("Firmware update has failed due to a connection or an installation error. TODO: what to do now? Check your cable connection...") }}
        </p>
        <a class="button-next" href="{{ url("wizard_step", number=5) }}">{{ _("Next") }}</a>
    </div>
</div>

<script>
    $(document).ready(function() {
        ForisWizard.runUpdater();
    });
</script>