%rebase wizard/base **locals()

<div id="wizard-updater">
    <h1>Test připojení a kontrola aktualizací</h1>
    Probíhá kontrola dostupných aktualizací. Chvilku strpení...<br>
    <img src="/static/img/loader.gif" alt="Probíhá načítání...">
    <div id="wizard-updater-status"></div>
</div>

<script>
    $(document).ready(function() {
        ForisWizard.runUpdater();
    });
</script>