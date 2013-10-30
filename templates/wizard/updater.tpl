%rebase wizard/base **locals()

<div id="wizard-updater">
    <h1>Test připojení a kontrola aktualizací</h1>
    <div id="updater-progress" class="background-progress">
        <img src="/static/img/loader.gif" alt="Probíhá načítání..."><br>
        Probíhá kontrola dostupných aktualizací.<br>
        Chvilku strpení...<br>
        <div id="wizard-updater-status"></div>
    </div>
    <div id="updater-success">
        <img src="/static/img/success.png" alt="Hotovo"><br>
        <p>Aktualizace proběhla v pořádku, můžete postoupit k dalšímu kroku.</p>
        <a class="button-next" href="/wizard/step/5">Next</a>
    </div>
    <div id="updater-fail">
        <img src="/static/img/fail.png" alt="Chyba"><br>
        <p>
            Aktualizace se nepodařilo stáhnout nebo došlo k chybě. Pokud Vaše připojení...
            <!-- TODO: blabla -->
        </p>
        <a class="button-next" href="/wizard/step/5">Next</a>
    </div>
</div>

<script>
    $(document).ready(function() {
        ForisWizard.runUpdater();
    });
</script>