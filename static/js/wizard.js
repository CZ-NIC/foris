var KruciWizard = {};

KruciWizard.validators = {
    // TODO: implement JS validators
    ipv4: null,
    integer: null,
    notnull: null,
    mac_address: null,
    in_range: null,
    len_range: null,
    fields_equal: null
};

KruciWizard.updateForm = function() {
    var form = $("#wizard-form");
    form.css("background-color", "red");
    $.post(form.attr("action"), form.serialize())
            .done(function(data){
                form.replaceWith(data.html);
                form.css("background-color", "inherit");
            });
};

KruciWizard.callAjaxAction = function(wizardStep, action) {
    return $.get("/wizard/step/" + wizardStep + "/ajax", {action: action});
};

KruciWizard.ntpUpdate = function() {
    KruciWizard.callAjaxAction("3", "ntp_update")
        .done(function(data) {
            if (data.success) {
                $("#wizard-time").empty().append("<p>Bazinga! Jdeme dál.</p>")
            }
            else {
                KruciWizard.showTimeForm();
            }
        });
};

KruciWizard.runUpdater = function () {
    KruciWizard.callAjaxAction("4", "run_updater")
        .done(function(data) {
            console.log(data);
            if (data.success)
                KruciWizard.checkUpdaterStatus();
            else
                console.log("TODO: SHIT HAPPENED");
        });
};

KruciWizard.checkUpdaterStatus = function() {
    KruciWizard.callAjaxAction("4", "updater_status")
        .done(function(data) {
            var updaterStatus = $("#wizard-updater-status");
            updaterStatus.empty().append(data.status);
            if (data.status == "failed") {
                console.log(data.message);
                updaterStatus.append("<p>Chyba: " + data.message + "</p>")
            }
            else if (data.status == "running") {
                // timeout is better, because we won't get multiple requests stuck processing
                // real delay between status updates is then delay + request_processing_time
                window.setTimeout(KruciWizard.checkUpdaterStatus, 1000);
            }
        });
};

KruciWizard.showTimeForm = function() {
    KruciWizard.callAjaxAction("3", "time_form")
        .done(function(data) {
            $("#wizard-time").empty().append(data.form);
        });
};


// TODO: maybe move somewhere else...
$(document).ready(function(){
    $(document).on("change", ".has-requirements", function(){
        KruciWizard.updateForm();
    });
});