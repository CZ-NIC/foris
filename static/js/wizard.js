var ForisWizard = {};

ForisWizard.validators = {
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

ForisWizard.runValidator = function(validator, value, mangledArgs) {
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

ForisWizard.validateField = function(field) {
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
        if (validators.hasOwnProperty(i) && ForisWizard.validators.hasOwnProperty(validators[i])) {
            var args = field.data("validator-" + validators[i]);
            var result = ForisWizard.runValidator(validators[i], field.val(), args);
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


ForisWizard.validateForm = function(form) {
    var inputs = $("input.validate", form);
    console.log(inputs);
    for (var i in inputs) {
        if (inputs.hasOwnProperty(i) && !ForisWizard.validateField(inputs[i]))
            return false;
    }
    return true;
};


ForisWizard.updateForm = function() {
    var form = $("#wizard-main-form");
    form.css("background-color", "red");
    $.post(form.attr("action"), form.serialize())
            .done(function(data){
                form.replaceWith(data.html);
                form.css("background-color", "inherit");
            });
};

ForisWizard.callAjaxAction = function(wizardStep, action) {
    return $.get("/wizard/step/" + wizardStep + "/ajax", {action: action});
};

ForisWizard.ntpUpdate = function() {
    ForisWizard.callAjaxAction("3", "ntp_update")
        .done(function(data) {
            if (data.success) {
                $("#time-progress").hide();
                $("#time-success").show();
            }
            else {
                ForisWizard.showTimeForm();
            }
        });
};

ForisWizard.runUpdater = function () {
    ForisWizard.callAjaxAction("4", "run_updater")
        .done(function(data) {
            console.log(data);
            if (data.success)
                ForisWizard.checkUpdaterStatus();
            else {
                $("#updater-progress").hide();
                $("#updater-fail").show();
            }
        });
};

ForisWizard.checkUpdaterStatus = function() {
    ForisWizard.callAjaxAction("4", "updater_status")
        .done(function(data) {
            if (data.status == "failed") {
                console.log(data.message);
                $("#updater-progress").hide();
                $("#updater-fail").show(); // TODO: determine what caused the fail, maybe?
            }
            else if (data.status == "running") {
                // timeout is better, because we won't get multiple requests stuck processing
                // real delay between status updates is then delay + request_processing_time
                window.setTimeout(ForisWizard.checkUpdaterStatus, 1000);
            }
            else if (data.status == "done") {
                $("#updater-progress").hide();
                $("#updater-success").show();
            }
        });
};

ForisWizard.showTimeForm = function() {
    ForisWizard.callAjaxAction("3", "time_form")
        .done(function(data) {
            $("#wizard-time").empty().append(data.form);
        });
};


// TODO: maybe move somewhere else...
// TODO: also, most of these "hooks" are not production-ready
$(document).ready(function(){
    $(document).on("change", ".has-requirements", function(){
        ForisWizard.updateForm();
    });

    $(document).on("keyup", ".validate", function() {
        ForisWizard.validateField(this);
    });

    $(document).on("submit", "form", function(e) {
        if (ForisWizard.validateForm(this)) {
            console.log("submitting!");
        }
        else {
            e.preventDefault();
            console.log("TODO: error in validation");  // TODO: warn
        }
    });
});