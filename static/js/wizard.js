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

ForisWizard.formValidators = {
    eqfields: function(form, args) {
        var argsArray = args.split("|");
        if (argsArray.length != 3 || !argsArray[0]
                || !argsArray[1] || !argsArray[2])
            return true; // wrong arguments
        var elOne = $("input[name=" + argsArray[0] + "]", form)
        var elTwo = $("input[name=" + argsArray[1] + "]", form)
        var errBox = $("#form-error-box");
        if (elOne.val() == elTwo.val()) {
            errBox.hide();
            return true;
        }
        else {
            errBox.text(argsArray[2]);
            errBox.show();
            elOne.val('');
            elTwo.val('');
            elOne.parent().find("div").remove();
            elTwo.parent().find("div").remove();
            elOne.focus();
            return false;
        }
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
        var fMarker = field.parent().find("[class|='field']");
        if (fMarker.length)
            fMarker.replaceWith('<div class="field-invalid"></div>');
        else
            field.parent().append('<div class="field-invalid"></div>');
    };

    var markOk = function() {
        var fMarker = field.parent().find("[class|='field']");
        if (fMarker.length)
            fMarker.replaceWith('<div class="field-valid"></div>');
        else
            field.parent().append('<div class="field-valid"></div>');
    };

    if (field.hasClass("required") && field.val() == "")
        markInvalid();

    if (!field.hasClass("validate") || !field.hasClass("required") && field.val() == "") {
        markOk();
        return true;
    }

    var validators = field.data("validators").split(" ");
    for (var i in validators) {
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
    // validate inputs
    var inputs = $("input.validate", form);
    for (var i in inputs) {
        if (inputs.hasOwnProperty(i) && !ForisWizard.validateField(inputs[i])) {
            return false;
        }
    }
    
    // validate form itself (relations between fields,...)
    var jQForm = $(form);
    var validators = jQForm.data("validators");
    if (validators)
        validators = validators.split(" ");
    else
        return true; // no form validators
    
    for (var i = 0; i < validators.length; i++) {
        if (ForisWizard.formValidators.hasOwnProperty(validators[i])) {
            var args = jQForm.data("validator-" + validators[i]);
            if (!ForisWizard.formValidators[validators[i]](form, args))
                // fail-fast
                return false;
        }
    }
    
    return true;
};

ForisWizard.updateForm = function() {
    var form = $("#main-form");
    form.css("background-color", "red");
    var serialized = form.serialize();
    $.post(form.attr("action"), serialized)
            .done(function(data){
                form.replaceWith(data.html);
                form.css("background-color", "inherit");
            });
    form.find("input, select, button").attr("disabled", "disabled");
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
                $("#updater-progress").hide();
                $("#updater-fail").show(); // TODO: determine what caused the fail, maybe?
            }
            else if (data.status == "running") {
                // timeout is better, because we won't get multiple requests stuck processing
                // real delay between status updates is then delay + request_processing_time
                window.setTimeout(ForisWizard.checkUpdaterStatus, 1000);
                // Show what has been installed already
                var log = data.last_activity;
                // TODO: Is there a better way than to accumulate it? Some kind of map + join?
                var div = $("#wizard-updater-status");
                div.empty();
                var ul = $("<ul>");
                div.append(ul);
                var log_html = "<ul>";
                for (var i in log) {
                        var item = log[i];
                        var li = $("<li>");
                        var mode;
                        if (item[0] == 'remove') {
                                mode = '-';
                        } else {
                                mode = '+';
                        }
                        li.html(mode + item[1]);
                        ul.append(li);
                }
                div.show();
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
            var timeField = $("#wizard-time").empty().append(data.form)
                .find("input[name=\"time\"]");
            $(".form-fields").hide();
            $("#wizard-time-sync-auto").click(function() {
                timeField.val(new Date().toISOString());
                $("#wizard-time-sync-success").show();
            });
            $("#wizard-time-sync-manual").click(function() {
                $(".form-fields").show();
                $(this).hide();
            });
            ForisWizard.timeField = timeField;
            // there's a slight time drift, but it's not an issue here...
            window.setTimeout(ForisWizard.timeUpdateCallback, 1000);
        });
};

ForisWizard.timeUpdateCallback = function() {
    if (ForisWizard.timeField.is(":focus"))
        return;
    var newTime = new Date(ForisWizard.timeField.val());
    newTime.setMilliseconds(newTime.getMilliseconds() + 1000);
    ForisWizard.timeField.val(newTime.toISOString());
    window.setTimeout(ForisWizard.timeUpdateCallback, 1000);
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
        if (!ForisWizard.validateForm(this)) {
            e.preventDefault();
            // console.log("TODO: error in validation");
        }
    });
});
