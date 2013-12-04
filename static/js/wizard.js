/**
* Foris - web administration interface for OpenWrt based on NETCONF
* Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
*
* This program is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/
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
        if (argsArray.length != 3 || !argsArray[0] || !argsArray[1] || !argsArray[2]) {
            console.error("eqfields validator received invalid arguments.");
            return true;
        }

        var elOne = $("#field-" + argsArray[0], form);
        var elTwo = $("#field-" + argsArray[1], form);
        var errorBox = ForisWizard.getFormErrorBox(form);
        console.log(errorBox);
        if (elOne.val() == elTwo.val()) {
            errorBox.hide();
            return true;
        }
        else {
            errorBox.text(argsArray[2]);
            errorBox.show();
            ForisWizard.markInvalid(elTwo);
            // remove flag on focus
            $(document).on("focus", "#field-" + argsArray[1], function(e) {
                $(document).off(e);
                $("#field-" + argsArray[1]).parent().find("[class|='field-validation']").remove();
                errorBox.hide();
            });
            return false;
        }
    }
};

ForisWizard.initialize = function() {
    $(document).on("change", ".has-requirements", function() {
        $(this).after('<img src="/static/img/icon-loading.gif" class="field-loading" alt="Loading...">');
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
};

ForisWizard.markInvalid = function(field) {
    var fMarker = field.parent().find("[class|='field-validation']");
    if (fMarker.length)
        fMarker.replaceWith('<div class="field-validation-fail"></div>');
    else
        field.parent().append('<div class="field-validation-fail"></div>');
};

ForisWizard.markOk = function(field) {
    var fMarker = field.parent().find("[class|='field-validation']");
    if (fMarker.length)
        fMarker.replaceWith('<div class="field-validation-pass"></div>');
    else
        field.parent().append('<div class="field-validation-pass"></div>');
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
    var result = true;
    field = $(field);

    if (field.hasClass("required") && field.val() == "")
        this.markInvalid(field);

    if (!field.hasClass("validate") || !field.hasClass("required") && field.val() == "") {
        this.markOk(field);
    }


    var validators = field.data("validators");
    if (validators) {
        validators = validators.split(" ");
        for (var i in validators) {
            if (validators.hasOwnProperty(i) && ForisWizard.validators.hasOwnProperty(validators[i])) {
                var args = field.data("validator-" + validators[i]);
                var res = ForisWizard.runValidator(validators[i], field.val(), args);
                result = result && res;
            }
        }
    }

    if (result) {
        this.markOk(field);
    }
    else {
        this.markInvalid(field);
    }

    return result;
};

ForisWizard.getFormErrorBox = function(form) {
    var errorBox = $("#form-error-box");
    if (errorBox.length)
        return errorBox;

    $(form).after('<div id="form-error-box"></div>');
    return $("#form-error-box");
};

ForisWizard.validateForm = function(form) {
    var result = true;
    // validate inputs
    var inputs = $("input.validate", form);
    for (var i in inputs) {
        if (inputs.hasOwnProperty(i) && !ForisWizard.validateField(inputs[i])) {
            result = false;
        }
    }
    
    // validate form itself (relations between fields,...)
    var jQForm = $(form);
    var validators = jQForm.data("validators");
    if (validators)
        validators = validators.split(" ");
    else
        return result; // no form validators

    for (var i = 0; i < validators.length; i++) {
        if (ForisWizard.formValidators.hasOwnProperty(validators[i])) {
            var args = jQForm.data("validator-" + validators[i]);
            if (!ForisWizard.formValidators[validators[i]](form, args))
                result = false;
                break;
        }
    }
    
    return result;
};

ForisWizard.updateForm = function() {
    var form = $("#main-form");
    var serialized = form.serialize();
    $.post(form.attr("action"), serialized)
            .done(function(data){
                form.replaceWith(data.html);
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

ForisWizard.updateWiFiQR = function (ssid, password, hidden) {
    var codeElement = $("#wifi-qr");
    codeElement.empty();

    if (!$("#field-wifi_enabled_1").prop("checked"))
        return;

    if (hidden)
        hidden = 'H:true';

    codeElement.empty().qrcode({
        width: 220,
        height: 220,
        text: 'WIFI:T:WPA;S:"' + ssid + '";P:"' + password + '";' + hidden + ';'
    });
};

ForisWizard.initWiFiQR = function () {
    // NOTE: make sure that jquery.qrcode is loaded on the page that's using
    // this method. Alternatively, it could be loaded using $.getScript() here.

    var doRender = function () {
        doRender.debounceTimeout = null;
        ForisWizard.updateWiFiQR(
            $("#field-ssid").val(),
            $("#field-key").val(),
            $("#field-ssid_hidden_1").prop("checked"));
    };
    doRender();

    $(document).on("change keyup", "#field-ssid, #field-key, #field-ssid_hidden_1", function () {
        clearTimeout(doRender.debounceTimeout);
        doRender.debounceTimeout = setTimeout(doRender, 500);
    });
};


$(document).ready(function(){
    ForisWizard.initialize();
});
