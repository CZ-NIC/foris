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
var Foris = {
  messages: {
    qrErrorPassword: "Your password contains non-standard characters. These are not forbidden, but could cause problems on some devices.",
    qrErrorSSID: "Your SSID contains non-standard characters. These are not forbidden, but could cause problems on some devices.",
    ok: "OK",
    error: "Error",
    loading: "Loading...",
    checkNoForward: "Connectivity test failed, testing connection with disabled forwarding.",
    lanIpChanged: 'The IP address of your router has been changed. It should be accessible from <a href="%NEW_LOC%">%IP_ADDR%</a>. See the note above for more information about IP address change.',
    confirmRestart: "Are you sure you want to restart the router?",
    confirmRestartExtra: "\nRemaining unread messages (%UNREAD%) will be deleted.",
    unsavedNotificationsAlert: "There are some unsaved changes in the notifications settings.\nDo you want to discard them and test the notifications with the old settings?"
  }
};

Foris.initialize = function () {
  $(document).on("change", ".has-requirements", function () {
    var input = $(this);
    input.parent().append('<img src="/static/img/icon-loading.gif" class="field-loading" alt="' + Foris.messages.loading + '">');
    Foris.updateForm(input.closest("form"));
  });

  Foris.initParsley();
  Foris.initLanChangeDetection();
  Foris.initClickableHints();
  Foris.initSmoothScrolling();
  Foris.applySVGFallback();
};

Foris.initParsley = function () {
  $("form").each(function () {
    $(this).parsley({
      excluded: 'input[type=button], input[type=submit], input[type=reset], input[type=hidden], input[type=radio]',
      trigger: "keyup change paste",
      successClass: "field-validation-pass",
      errorClass: "field-validation-fail",
      errorsWrapper: '<ul class="validation-errors"></ul>',
      errorsContainer: function (parsleyField) {
        var container = parsleyField.$element.parent().find(".validation-container");
        if (container.length === 0) {
          // if field is not validated by Parsley
          if (parsleyField.constraints && !parsleyField.constraints.length) {
            // we must return something...
            container = $("<div></div>");
          }
          else {
            container = $("<div class='validation-container'></div>")
                .appendTo(parsleyField.$element.parent());
          }
        }
        return container;
      }
    });
  });

  $.listen("parsley:field:success", function(parsleyField) {
    parsleyField.$element.parent().parent().find(".server-validation-container").remove();

  });

  $.listen("parsley:field:error", function(parsleyField) {
    parsleyField.$element.parent().parent().find(".server-validation-container").remove();
  });

};

Foris.initLanChangeDetection = function () {
  var lanIpChanged = false;
  $(document).on("change paste", "[name=lan_ipaddr]", function () {
    var lanField = this;
    if (!Foris.lanIpChanged) {
      lanIpChanged = true;
      $(document).on("submit", "#main-form", function () {
        // if the value really changed from the default
        if (lanField.defaultValue != lanField.value) {
          var newLocation = document.location.protocol + "//" + lanField.value + "/?next=" + document.location.pathname;
          $(".config-description, .wizard-description").after('<div class="message info">' + Foris.messages.lanIpChanged.replace(/%IP_ADDR%/g, lanField.value).replace(/%NEW_LOC%/g, newLocation) + '</div>');
          // if the page was accessed from the old IP address, wait 10 seconds and do a redirect
          window.setTimeout(function () {
            if (lanField.defaultValue == document.location.hostname) {
              document.location.href = newLocation;
            }
          }, 10000);
        }
      });
    }
  });
};

Foris.initClickableHints = function () {
  $(document).on("click", ".field-hint", function() {
    var $this = $(this);
    var hintHTML = $this.next(".hint-text");
    if (hintHTML.length) {
      if (hintHTML.is(":visible"))
        hintHTML.slideUp();
      else
        hintHTML.slideDown();
      return;
    }
    hintHTML = $('<div class="hint-text">' + this.getAttribute("title") + '</div>');
    $this.after(hintHTML);
    hintHTML.slideDown();
  });
};

Foris.initSmoothScrolling = function () {
  $(".menu-link").click(function(e) {
    e.preventDefault();
    $('html,body').animate({
      scrollTop: $(this.hash).offset().top
    })
  });
};

Foris.applySVGFallback = function() {
  if (!document.implementation.hasFeature("http://www.w3.org/TR/SVG11/feature#Image", "1.1")) {
    $("img[src$='.svg']").attr("src", function() {
      var src = this.src.split('.');
      var ext = src.pop();
      if (ext != "svg") return;
      src.push("png");
      this.src = src.join(".");
    });
  }
};

Foris.updateForm = function (form) {
  var serialized = form.serializeArray();
  var idSelector = form.attr("id") ? " #" + form.attr("id") : "";
  form.load(form.attr("action") + idSelector, serialized, function (response, status, xhr) {
    try {
      var jsonResponse = JSON.parse(response);
      if (jsonResponse.loggedOut && jsonResponse.loginUrl) {
        window.location.replace(jsonResponse.loginUrl);
        return;
      }
    }
    catch (err) {
      // SyntaxError when response is not JSON - do nothing
    }

    $(this).children(':first').unwrap();
    Foris.initParsley();
  });
  form.find("input, select, button").attr("disabled", "disabled");
};

Foris.callAjaxAction = function (wizardStep, action, timeout) {
  timeout = timeout || 0;
  return $.ajax({
    url:"/wizard/step/" + wizardStep + "/ajax",
    data: {action: action},
    timeout: timeout
  });
};

Foris.connectivityCheck = function () {
  Foris.callAjaxAction("3", "check_connection")
      .done(function (data) {
        if (data.result == "ok") {
          $("#connectivity-progress").hide();
          $("#connectivity-success").show();
        }
        else if (data.result == "no_dns") {
          Foris.connectivityCheckNoForward();
        }
        else {
          // no_connection or error
          $("#connectivity-progress").hide();
          $("#connectivity-fail").show();
        }
      });
};

Foris.connectivityCheckNoForward = function () {
  $("#wizard-connectivity-status").html("<p>" + Foris.messages.checkNoForward + "</p>");
  Foris.callAjaxAction("3", "check_connection_noforward")
      .done(function (data) {
        if (data.result == "ok") {
          $("#connectivity-progress").hide();
          $("#connectivity-success").show();
        }
        else if (data.result == "no_dns") {
          $("#connectivity-progress").hide();
          $("#connectivity-nodns").show();
        }
        else {
          // no_connection or error
          $("#connectivity-progress").hide();
          $("#connectivity-fail").show();
        }
      });
};

Foris.ntpUpdate = function () {
  Foris.callAjaxAction("4", "ntp_update")
      .done(function (data) {
        if (data.success) {
          $("#time-progress").hide();
          $("#time-success").show();
        }
        else {
          Foris.showTimeForm();
        }
      });
};

Foris.runUpdater = function () {
  Foris.callAjaxAction("5", "run_updater")
      .done(function (data) {
        if (data.success)
          Foris.checkUpdaterStatus();
        else {
          $("#updater-progress").hide();
          $("#updater-fail").show();
        }
      });
};

Foris.checkUpdaterStatus = function (retries, pageNumber) {
  if (retries == null)
    retries = 0;

  if (pageNumber == null)
    pageNumber = 5;

  // we need longer retry time for second update page - router is restarted there
  var maxRetries = pageNumber == 6 ? 45 : 10;

  Foris.callAjaxAction(pageNumber, "updater_status", 3000)
      .done(function (data) {
        retries = 0;  // reset retries in case of success
        if (data.success === false) {
          if (data.loggedOut && data.loggedOut === true) {
            $("#updater-progress").hide();
            $("#updater-login").show();
          }
          return;
        }
        if (data.status == "failed") {
          $("#updater-progress").hide();
          $("#updater-fail").show();
        }
        else if (data.status == "running") {
          // timeout is better, because we won't get multiple requests stuck processing
          // real delay between status updates is then delay + request_processing_time
          window.setTimeout(function() {
            Foris.checkUpdaterStatus(retries, pageNumber)
          }, 1000);
          // Show what has been installed already
          var log = data.last_activity;
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
            } else if(item[0] == 'download') {
              mode = '↓';
            }
            else {
              mode = '+';
            }
            li.html(mode + item[1]);
            ul.append(li);
          }
          div.show();
        }
        else if (data.status == "offline_pending") {
          window.setTimeout(function() {
            Foris.checkUpdaterStatus(retries, pageNumber)
          }, 1000);
        }
        else if (data.status == "done") {
          $("#updater-progress").hide();
          $("#updater-success").show();
        }
      })
      .fail(function () {
        // try multiple times (in one-second retries) in case the server is restarting
        if (retries < maxRetries) {
          retries += 1;
          window.setTimeout(function () {
            Foris.checkUpdaterStatus(retries, pageNumber)
          }, 1000);
        }
        else {
          $("#updater-progress").hide();
          $("#updater-fail").show();
        }
      })
};

Foris.showTimeForm = function () {
  Foris.callAjaxAction("4", "time_form")
      .done(function (data) {
        var timeField = $("#wizard-time").empty().append(data.form)
            .find("input[name=\"time\"]");
        $(".form-fields").hide();
        $("#wizard-time-sync-auto").click(function (e) {
          e.preventDefault();
          timeField.val(new Date().toISOString());
          $("#wizard-time-sync-success").show();
        });
        $("#wizard-time-sync-manual").click(function (e) {
          e.preventDefault();
          $(".form-fields").show();
          $(this).hide();
        });
        Foris.timeField = timeField;
        // there's a slight time drift, but it's not an issue here...
        window.setTimeout(Foris.timeUpdateCallback, 1000);
      });
};

Foris.timeUpdateCallback = function () {
  if (Foris.timeField.is(":focus"))
    return;
  var newTime = new Date(Foris.timeField.val());
  newTime.setMilliseconds(newTime.getMilliseconds() + 1000);
  Foris.timeField.val(newTime.toISOString());
  window.setTimeout(Foris.timeUpdateCallback, 1000);
};

Foris.checkLowerAsciiString = function (string) {
  for (var i = 0; i < string.length; i++) {
    var charCode = string.charCodeAt(i);
    if (charCode < 32 || charCode > 127) {
      return false;
    }
  }
  return true;
};

Foris.updateWiFiQR = function (ssid, password, hidden) {
  var codeElement = $("#wifi-qr");
  codeElement.empty();

  if (!$("#field-wifi_enabled_1").prop("checked"))
    return;


  var showQRError = function (message) {
    codeElement.append("<div class=\"qr-error\">" + message + "</div>");
  };

  if (!Foris.checkLowerAsciiString(ssid)) {
    showQRError(Foris.messages.qrErrorSSID);
    return;
  }
  if (!Foris.checkLowerAsciiString(password)) {
    showQRError(Foris.messages.qrErrorPassword);
    return;
  }

  if (hidden)
    hidden = 'H:true';
  else
    hidden = '';

  codeElement.empty().qrcode({
    size: 200,
    text: 'WIFI:T:WPA;S:"' + ssid + '";P:"' + password + '";' + hidden + ';'
  });
};

Foris.initWiFiQR = function () {
  // NOTE: make sure that jquery.qrcode is loaded on the page that's using
  // this method. Alternatively, it could be loaded using $.getScript() here.

  var doRender = function () {
    doRender.debounceTimeout = null;
    Foris.updateWiFiQR(
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

Foris.initNotifications = function (csrf_token) {
  $(".notification .reboot").on("click", function() {
    var unread = $(".notification:visible").length - 1;
    var extraMessage = "";
    if (unread > 0)
      extraMessage = Foris.messages.confirmRestartExtra.replace(/%UNREAD%/g, unread);
    return confirm(Foris.messages.confirmRestart + extraMessage);
  });

  $(".notification .dismiss").on("click", function(e) {
    e.preventDefault();
    var id = $(this).data("id");
    $.post("/config/notifications/dismiss",
        {
          message_ids: [id],
          csrf_token: csrf_token
        },
        function(data) {
          if (data.success) {
            for (var i=0; i < data.displayedIDs.length; i++) {
              $("#notification_" + data.displayedIDs[i]).fadeOut(800);
            }
          }
        }
    );
  });
};

Foris.initNotificationTestAlert = function () {
  var showNotificationTestAlert = false;

  $(document).on("change keyup paste", "#notifications-form", function () {
    showNotificationTestAlert = true;
  });

  $(document).on("click", "#notifications-test", function () {
    if (showNotificationTestAlert) {
      if (confirm(Foris.messages.unsavedNotificationsAlert)) {
        $("#notifications-form")[0].reset();
        return true;
      }
      return false;
    }
  });
};

$(document).ready(function () {
  Foris.initialize();
});
