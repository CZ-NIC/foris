var KruciWizard = {};

KruciWizard.validators = {
    ipv4: function(value) {
        var re_ipv4 = /^(\d{1,3}\.){3}\d{1,3}$/;
        return value.search(re_ipv4) != -1;
    },
    integer: function(value) {
        var re_integer = /^\d+$/;
        return value.search(re_integer) != -1;
    },
    notempty: function(value) {
        return value != "";
    },
    macaddress: function(value) {
        var re_macaddr = /^([a-fA-F0-9]{2}:){5}[a-fA-F0-9]{2}$/;
        return value.search(re_macaddr) != -1;
    },
    inrange: function(value, lo, hi) {
        return value >= lo && value <= hi;
    },
    lenrange: function(value, lo, hi) {
        return value.length >= lo && value.length <= hi;
    }
};

KruciWizard.runValidator = function(validator, value, mangledArgs) {
    if (!mangledArgs)
        return this.validators[validator](value);
    var argsArray = mangledArgs.split("|");
    if (mangledArgs && argsArray.length == 0)
        return this.validators[validator](value);
    if (argsArray.length == 1)
        return this.validators[validator](value, argsArray[0]);
    if (argsArray.length == 2)
        return this.validators[validator](value, argsArray[0], argsArray[1]);
    if (argsArray.length == 3)
        return this.validators[validator](value, argsArray[0], argsArray[1], argsArray[2]);
};

KruciWizard.validateField = function(field) {
    field = $(field);

    var markInvalid = function() {
        field.css("background", "red");
    };

    var markOk = function() {
        field.css("background", "inherit");
    };

    if (field.hasClass("required") && field.val() == "")
        markInvalid();

    if (!field.hasClass("validate"))
        return true;

    var validators = field.data("validators").split(" ");
    for (var i in validators) {
        console.log("checking for validator " + validators[i]);
        if (validators.hasOwnProperty(i) && KruciWizard.validators.hasOwnProperty(validators[i])) {
            var args = field.data("validator-" + validators[i]);
            var result = KruciWizard.runValidator(validators[i], field.val(), args);
            if (result) {
                markOk();
            }
            else {
                markInvalid();
                return false;
            }
        }
    }
    return true;
};


KruciWizard.validateForm = function(form) {
    var inputs = $("input.validate", form);
    console.log(inputs);
    for (var i in inputs) {
        if (inputs.hasOwnProperty(i) && !KruciWizard.validateField(inputs[i]))
            return false;
    }
    return true;
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
// TODO: also, most of these "hooks" are not production-ready
$(document).ready(function(){
    $(document).on("change", ".has-requirements", function(){
        KruciWizard.updateForm();
    });

    $(document).on("keyup", ".validate", function() {
        KruciWizard.validateField(this);
    });

    $(document).on("submit", "form", function(e) {
        if (KruciWizard.validateForm(this)) {
            console.log("submitting!");
        }
        else {
            e.preventDefault();
            console.log("TODO: error in validation");  // TODO: warn
        }
    });
});