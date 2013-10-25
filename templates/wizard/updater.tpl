%if not defined('is_xhr'):
    %rebase _layout **locals()
%end

<div id="wizard-updater">
    Probíhá kontrola dostupných aktualizací. Chvilku strpení...
    <div id="wizard-updater-status"></div>
</div>

<script>
    $(document).ready(function() {
        ForisWizard.runUpdater();
    });
</script>