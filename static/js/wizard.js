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

ForisWizard.initialize = function() {
    $(document).on("change", ".has-requirements", function() {
        $(this).parent().append('<img src="/static/img/icon-loading.gif" class="field-loading" alt="Loading...">');
        ForisWizard.updateForm();
    });

    ForisWizard.initParsley();
};

ForisWizard.initParsley = function() {
    $("form").parsley({
        namespace: "data-parsley-",
        trigger: "keyup change paste",
        successClass: "field-validation-pass",
        errorClass: "field-validation-fail",
        errorsWrapper: '<ul class="validation-errors"></ul>',
        errors: {
          container: function(elem, isRadioOrCheckbox) {
            var container = elem.parent().find(".validation-container");
            if (container.length === 0) {
              container = $("<div class='validation-container'></div>").appendTo(elem.parent());
            }
            return container;
          }
        },
        listeners: {
          onFieldSuccess: function ( elem, constraints, ParsleyField ) {
            elem.parent().find(".server-validation-container").remove();
          },
          onFieldError: function ( elem, constraints, ParsleyField ) {
            elem.parent().find(".server-validation-container").remove();
          }
        }
    });
};

ForisWizard.updateForm = function() {
    var form = $("#main-form");
    var serialized = form.serialize();
    $.post(form.attr("action"), serialized)
            .done(function(data){
                form.replaceWith(data.html);
                ForisWizard.initParsley();
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

ForisWizard.checkUpdaterStatus = function(retries) {
    if (retries == null)
        retries = 0;

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
        })
        .fail(function() {
            // wait 5 seconds (in one-second retries) in case the server is restarting
            if (retries < 5) {
                retries += 1;
                window.setTimeout(function() {
                    ForisWizard.checkUpdaterStatus(retries)}, 1000);
            }
            else {
                $("#updater-progress").hide();
                $("#updater-fail").show();
            }
        })
};

ForisWizard.showTimeForm = function() {
    ForisWizard.callAjaxAction("3", "time_form")
        .done(function(data) {
            var timeField = $("#wizard-time").empty().append(data.form)
                .find("input[name=\"time\"]");
            $(".form-fields").hide();
            $("#wizard-time-sync-auto").click(function(e) {
                e.preventDefault();
                timeField.val(new Date().toISOString());
                $("#wizard-time-sync-success").show();
            });
            $("#wizard-time-sync-manual").click(function(e) {
                e.preventDefault();
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

ForisWizard.checkLowerAsciiString = function (string) {
    for (var i=0; i < string.length; i++) {
        var charCode = string.charCodeAt(i);
        if (charCode < 32 || charCode > 127) {
            return false;
        }
    }
    return true;
};

ForisWizard.updateWiFiQR = function (ssid, password, hidden) {
    var codeElement = $("#wifi-qr");
    codeElement.empty();

    if (!$("#field-wifi_enabled_1").prop("checked"))
        return;


    var showQRError = function(message) {
        codeElement.append("<div class=\"qr-error\">" + message + "</div>");
    };

    if (!ForisWizard.checkLowerAsciiString(ssid)) {
        showQRError("Vámi zadané jméno sítě obsahuje nestandardní znaky, které nejsou zakázané, avšak mohou na některých zařízeních způsobovat problémy.");  // TODO: l10n (see #3022)
        return;
    }
    if (!ForisWizard.checkLowerAsciiString(password)) {
        showQRError("Vámi zadané heslo obsahuje nestandardní znaky, které nejsou zakázané, avšak mohou na některých zařízeních způsobovat problémy.");  // TODO: l10n (see #3022)
        return;
    }

    if (hidden)
        hidden = 'H:true';
    else
        hidden = '';

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

    $(document).on("change keyup paste", "#field-ssid, #field-key, #field-ssid_hidden_1", function () {
        clearTimeout(doRender.debounceTimeout);
        doRender.debounceTimeout = setTimeout(doRender, 500);
    });
};


$(document).ready(function(){
    ForisWizard.initialize();
});
