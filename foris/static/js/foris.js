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
    qrErrorPassword: "",
    qrErrorSSID: "",
    ok: "",
    error: "",
    loading: "",
    checkNoForward: "",
    lanIpChanged: "",
    confirmDisabledUpdates: "",
    confirmDisabledDNSSEC: "",
    confirmRestart: "",
    confirmRestartExtra: "",
    unsavedNotificationsAlert: ""
  }
};

// do some magic to find CGI SCRIPT_NAME - must be run exactly when script is parsed
(function (window, Foris) {
  try {
    var scripts = window.document.getElementsByTagName('script');
    var pathname = extractPathName(scripts[scripts.length - 1].src);
    Foris.scriptname = pathname.substr(0, pathname.indexOf("/static"));
  } catch (e) {
    Foris.scriptname = "";
  }
})(window, Foris);


Foris.initialize = function () {
  $(document).on("change", ".has-requirements", function () {
    var input = $(this);
    input.parent().append('<img src="' + Foris.scriptname + '/static/img/icon-loading.gif" class="field-loading" alt="' + Foris.messages.loading + '">');
    Foris.updateForm(input.closest("form"));
  });

  Foris.initParsley();
  Foris.initLanChangeDetection();
  Foris.initLanFormOverride();
  Foris.initClickableHints();
  Foris.initSmoothScrolling();
  Foris.applySVGFallback();
  Foris.initWebsockets();
  Foris.initRebootRequired();
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

Foris.initLanFormOverride = function () {
  var lanForm = $("#form-lan-buttons").parents("form:first");
  lanForm.submit(function(event) {
    event.preventDefault();
    $.ajax({
      type: "POST",
      url: lanForm.attr("action"),
      data: lanForm.serialize(),
      success: function(data) {
        // Nothing to be done here...
      },
      error: function(jqXHR, textStatu, errorThrown) {
      }
    });
  });
}

Foris.initLanChangeDetection = function () {
  var lanIpChanged = false;
  $(document).on("change paste", "[name=lan_ipaddr]", function () {
    var lanField = this;
    if (!Foris.lanIpChanged) {
      lanIpChanged = true;
      $(document).on("submit", "#main-form", function () {
        // if the value really changed from the default
        if (lanField.defaultValue != lanField.value) {
          var newLocation = document.location.protocol + "//" + lanField.value + Foris.scriptname + "/?next=" + document.location.pathname;
          $(".config-description, .wizard-description").after('<div class="message info">' + Foris.messages.lanIpChanged.replace(/%NEW_IP_LINK%/g, '<a href="' + newLocation + '">' + lanField.value + '</a>') + '</div>');
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
    if (hintHTML.is(":visible"))
      hintHTML.slideUp();
    else
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


Foris.WS = {
  maintain: function(msg) {
    switch (msg.action) {
        case "reboot":
            Foris.handleReboot(msg.data.new_ips);
            break;
        case "reboot_required":
            $('#reboot-required-notice').show("slow");
            break;;
    }
  },
  lan: function(msg) {
    Foris.handleLanRestart(msg.data.ip);
  },
  router_notifications: function(msg) {
    if (msg.action == "create" || msg.action == "mark_as_displayed") {
        Foris.handleNotificationsCountUpdate(msg.data.new_count);
    }
  },
  updater: function(msg) {
    if (msg.action == "run") {
        Foris.handleUpdaterRun(msg.data.status != "exit" && msg.data.status != "failed");
    }
  }
};

Foris.initWebsockets = function() {
  // Right now url is hardcoded to ws(s)://<this_domain>[:<this_port>]/foris-ws
  // It might be to set this url as cmdline argument in the future
  var port = window.location.port == "" ? "" : ":" + window.location.port;
  var protocol = window.location.protocol == "http:" ? "ws:" : "wss:";
  var url = protocol + "//" + window.location.hostname + port + "/foris-ws";

  // Connect to foris-ws
  ws = new WebSocket(url);

  ws.onopen = function () {
    var output = JSON.stringify({"action": "subscribe", "params": Object.keys(Foris.WS)});
    ws.send(output);
    console.log("WS registering for: " + Object.keys(Foris.WS));
  };

  ws.onmessage = function (e) {
    console.log("WS message received: " + e.data);
    var parsed = JSON.parse(e.data);
    if (Foris.WS.hasOwnProperty(parsed["module"])) {
      Foris.WS[parsed["module"]](parsed);
    }
  };

  ws.onerror = function(e) {
    console.log("WS error occured:" + e);
  };

  ws.onclose = function() {
    console.log("WS connection closed.");
  };

};

Foris.afterAjaxUpdateFunctions = [];
Foris.afterAjaxUpdate = function(response, status, xhr) {
  for (var i=0; i < Foris.afterAjaxUpdateFunctions.length; i++) {
    Foris.afterAjaxUpdateFunctions[i](response, status, xhr);
  }
}

Foris.updateForm = function (form) {
  var serialized = form.serializeArray();
  serialized.push({name: 'update', value: '1'});

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
    Foris.afterAjaxUpdate();
    $(document).trigger('formupdate', [form]);
  });
  form.find("input, select, button").attr("disabled", "disabled");
};

Foris.callAjaxAction = function (wizardStep, action, timeout) {
  timeout = timeout || 0;
  return $.ajax({
    url: Foris.scriptname + "/main/step/" + wizardStep + "/ajax",
    data: {action: action},
    timeout: timeout
  });
};

Foris.connectivityCheck = function (retries) {
  var maxRetries = 1;
  if (retries == null)
    retries = 0;

  Foris.callAjaxAction("3", "check_connection")
      .done(function (data) {
        if (data.result == "ok") {
          $("#connectivity-progress").hide();
          $("#connectivity-success").show();
        }
        else if (!retries || retries < maxRetries) {
          // Because the restart of the networking in the previous step takes
          // a while, it can take about ~10 seconds for the network to come up.
          // If the test fails, wait a few seconds and retry the test, so we
          // don't bother the user by forcing her to do a manual retry.
          window.setTimeout(function() { Foris.connectivityCheck(retries + 1) }, 6000);
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
  Foris.callAjaxAction("5", "ntp_update")
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
  $("#updater-progress").show();
  Foris.callAjaxAction("6", "run_updater")
      .done(function (data) {
        if (data.success)
          Foris.checkUpdaterStatus();
        else {
          $("#updater-progress").hide();
        }
      });
};

Foris.showUpdaterFail = function (data) {
  $("#updater-fail").show();
  if (data && data.message) {
    var messageEl = $('#updater-fail-message');
    messageEl.find('pre').text(data.message);
    messageEl.show();
  }
};

Foris.initEulaForm = function () {
  $("#updater-eula").show();

  $('#field-agreed_0').click(function () {
    return confirm(Foris.messages.confirmDisabledUpdates);
  });

  var eulaForm = $('#updater-eula-form');
  eulaForm.submit(function (e) {
    e.preventDefault();
    eulaForm.find("button").attr('disabled', 'disabled');
    $.ajax({
      url: eulaForm.attr('action'),
      method: 'post',
      data: eulaForm.serialize()
    })
        .done(function (data) {
          if (data.success) {
            if (data.redirect) {
              document.location.href  = data.redirect;
              return;
            }
            $('#updater-eula').hide();
            $("#updater-progress").show();
            Foris.checkUpdaterStatus();
          }
        });
  });
};


Foris.checkUpdaterStatus = function (retries, pageNumber) {
  if (retries == null)
    retries = 0;

  if (pageNumber == null)
    pageNumber = 6;

  // we need longer retry time for second update page - router is restarted there
  var maxRetries = pageNumber == 7 ? 45 : 10;

  Foris.callAjaxAction(pageNumber, "updater_status", 3000)
      .done(function (data) {
        var progressContainer = $("#updater-progress");
        progressContainer.show();
        retries = 0;  // reset retries in case of success
        if (data.success === false) {
          return;
        }
        if (data.status == "failed") {
          progressContainer.hide();
          Foris.showUpdaterFail(data);
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
          for (var i = log.length - 1; i >= 0; i--) {
            var item = log[i];
            var li = $("<li>");
            var mode;
            if (item[0] == 'remove') {
              mode = '-';
            } else if (item[0] == 'download') {
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
          progressContainer.hide();
          $("#updater-success").show();
        }
      })
      .fail(function (xhr) {
        // try multiple times (in one-second retries) in case the server is restarting
        if (retries < maxRetries) {
          retries += 1;
          window.setTimeout(function () {
            Foris.checkUpdaterStatus(retries, pageNumber)
          }, 1000);
        }
        else {
          $("#updater-progress").hide();
          if (xhr.responseJSON && xhr.responseJSON.loggedOut && xhr.responseJSON.loginUrl) {
            $("#updater-login").show();
          } else {
            Foris.showUpdaterFail();
          }
        }
      })
};

Foris.showTimeForm = function () {
  Foris.callAjaxAction("5", "time_form")
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

Foris.updateWiFiQR = function (radio, ssid, password, hidden) {
  var codeElement = $("#wifi-qr-" + radio);
  codeElement.empty();

  if (!$("#field-" + radio + "-device_enabled_1").prop("checked"))
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

  // determine present radios from wifi-enable checkboxes
  var radios = [];
  $("input[id$='-device_enabled_1']").each(function (i, el) {
    radios.push(el.getAttribute('id').replace(/field-(radio\d+)-.*/, '$1'));
  });

  var doRender = function (radio) {
    doRender.debounceTimeout = null;

    // create QR code for the radio and align its top with SSID input
    if (!document.getElementById('wifi-qr-' + radio)) {
      $('#wifi-qr').append('<div id="wifi-qr-' + radio + '" />');
    }

    var ssidInputPosition = $("input[id$='field-" + radio + "-ssid']").position();

    if (!ssidInputPosition)
      return;

    $('#wifi-qr-' + radio)
        .css('position', 'absolute')
        .css('right', 0)
        .css('top', ssidInputPosition.top);

    Foris.updateWiFiQR(
        radio,
        $('#field-' + radio + '-ssid').val(),
        $('#field-' + radio + '-password').val(),
        $('#field-' + radio + '-ssid_hidden_1').prop('checked'));
  };

  for (var i=0; i < radios.length; i++) {
    var radio = radios[i];

    doRender(radio);

    $(document).on('change keyup paste',
        '#field-' + radio + '-ssid, ' +
        '#field-' + radio + '-password, ' +
        '#field-' + radio + '-ssid_hidden_1',
        (function (r) {
          return function () {
            clearTimeout(doRender.debounceTimeout);
            doRender.debounceTimeout = setTimeout(function () {
              doRender(r)
            }, 500);
          }
        })(radio)
    );
  }

  $(document).on("formupdate", function () {
    for (var i = 0; i < radios.length; i++) {
      var radio = radios[i];
      doRender(radio);
    }
  });
};

Foris.initNotifications = function (csrf_token) {

  $(".notification .dismiss").on("click", function(e) {
    e.preventDefault();
    var id = $(this).data("id");
    $.post(Foris.scriptname + "/main/notifications/ajax",
        {
          action: "dismiss-notifications",
          notification_ids: [id],
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
  $(".notification.restart a").on("click", function(e) {
    e.preventDefault();
    var url = $(".notification.restart a").attr("href");
    $.get(url, {}, function(data){});
  });
  $("#dismiss-all-notifications").on("click", function(e) {
    e.preventDefault();
    var ids = [];
    var keep = false;
    $(".notification .dismiss").each(function(idx) {
      if ($(this).parent().find(".dismiss").length == 0) {
        keep = true;
      } else {
        ids.push($(this).data("id"));
      }
    });
    if (!keep) {
        $(this).hide();
    };
    $.post(Foris.scriptname + "/main/notifications/ajax",
        {
          action: "dismiss-notifications",
          notification_ids: ids,
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

Foris.waitForReachable = function(urls, data, handler_function, timeout) {
  var timeout = timeout || 1000;
  // wait function generator
  var genWaitForUrl = function(url) {
    var stored_data = data;
    return function() {
      var stored_handler = handler_function;
      var upper_function = arguments.callee;
      $.ajax({
        url: url,
        type: "GET",
        async: true,
        data: stored_data ? stored_data : {silent: true},
        crossDomain: true,
        headers: {'X-Requested-With': 'XMLHttpRequest'},
        success: function(data, text, jqXHR) {
          if (!stored_handler(url, jqXHR)) {
            setTimeout(upper_function, timeout);  // retry calling self later
          }
        },
        error: function(jqXHR, text, error) {
          if (!stored_handler(url, jqXHR)) {
            setTimeout(upper_function, timeout);  // retry calling self later
          }
        },
        timeout: timeout,
      });
    };
  }

  // start all functions
  for (var i = 0; i < urls.length; i++) {
    genWaitForUrl(urls[i])();
  }
};

Foris.waitForUnreachable = function(url, callback, timeout) {
  var timeout = timeout || 1000;
  // wait till current address is available
  var url = url;
  var unreachableFunction = function() {
    $.ajax({
      url: url,
      type: "GET",
      async: true,
      data: {silent: true},
      crossDomain: true,
      headers: {'X-Requested-With': 'XMLHttpRequest'},
      success: function(data, text, jqXHR) {
        setTimeout(unreachableFunction, timeout);
      },
      error: function(xhr, text, error) {
        callback(xhr, text, error);
      },
      timeout: timeout,
    });
  };
  unreachableFunction();
};

Foris.initRebootRequired = function() {
  $("#reboot-required-button").click(function(e) {
    var self = $(this);
    e.preventDefault();
    $.get(self.attr("href"));
  });
};

function extractPathName(src) {
  var a = document.createElement("a");
  a.href = src;

  return a.pathname;
}

function extractHost(src) {
  var a = document.createElement("a");
  a.href = src;

  return a.host;
}

Foris.handleReboot = function(ips) {
  $('#rebooting-notice').show("slow");
  $('#reboot-required-notice').hide("slow");

  var port = window.location.port == "" ? "" : ":" + window.location.port;
  var urls = [window.location.protocol + "//" + window.location.hostname + port + Foris.pingPath];
  for (var i = 0; i < ips.length; i++) {
    urls.push(window.location.protocol + "//" + ips[i] + port + Foris.pingPath);
  }

  var rebootDoneCallback = function(url, jqXHR) {
    if (jqXHR.status == 0) {
        return false;
    }
    if (jqXHR.status == 200) {
        if (jqXHR.responseJSON && jqXHR.responseJSON.loginUrl) {
            window.location = jqXHR.responseJSON.loginUrl;
        }
    }
    return false;
  }

  // start the machinery
  Foris.waitForUnreachable(window.location.pathname, function (xhr, text, error) {
    var pathname = window.location.pathname;
    Foris.waitForReachable(urls, {next: pathname}, rebootDoneCallback, 5000);
  });
};

Foris.handleLanRestart = function(ip) {
  $('#network-restart-notice').show("slow");

  var port = window.location.port == "" ? "" : ":" + window.location.port;
  var protocol = window.location.protocol;
  var pathname = window.location.pathname;
  var search = window.location.search;
  var urls = [
    window.location.protocol + "//" + window.location.hostname + port + Foris.pingPath,
    window.location.protocol + "//" + ip + port + Foris.pingPath
  ];

  var restartLanDoneCallback = function(url, jqXHR) {
    if (jqXHR.status == 0) {
        return false;
    }
    if (jqXHR.status == 200) {
        //if (jqXHR.responseJSON && jqXHR.responseJSON.loginUrl) {
        //    window.location = protocol + "//" + extractHost(url) + pathname + search;
        //}
        if (jqXHR.responseJSON && jqXHR.responseJSON.loginUrl) {
            window.location = jqXHR.responseJSON.loginUrl;
        }
    }
  }

  // start the machinery
  Foris.waitForUnreachable(window.location.pathname, function (xhr, text, error) {
    var pathname = window.location.pathname;
    Foris.waitForReachable(urls, {next: pathname}, restartLanDoneCallback);
  });
};

Foris.handleNotificationsCountUpdate = function(new_count) {
  var old_count = parseInt($("#notifications_menu_tag").text());
  $("#notifications_menu_tag").text(new_count);
  if (new_count > 0) {
    if (old_count > 0) {
      // blink
      $("#notifications_menu_tag").animate({opacity:0.05}, 200, "linear", function() {
        $(this).animate({opacity:1}, 200);
      });
    } else {
      // show
      $("#notifications_menu_tag").css('opacity', '0');
      $("#notifications_menu_tag").show();
      $("#notifications_menu_tag").animate({opacity:1}, 200);
    }
  } else {
    if (old_count > 0) {
      // hide
      $("#notifications_menu_tag").animate({opacity:0},200,"linear",function(){
        $(this).hide();
        $(this).css('opacity', '1');
      });
    } else {
      // already hidden do nothing
    }
  }
};

Foris.handleUpdaterRun = function(running) {
    if (running) {
      if (!$("#updater_menu_tag").is(":visible")) {
        $("#updater_menu_tag").css('opacity', '0');
        $("#updater_menu_tag").show();
        $("#updater_menu_tag").animate({opacity:1}, 200);
      }
    } else {
      if ($("#updater_menu_tag").is(":visible")) {
        $("#updater_menu_tag").animate({opacity:0},200,"linear",function(){
          $(this).hide();
          $(this).css('opacity', '1');
        });
      }
    }
};

$(document).ready(function () {
  Foris.initialize();

  $(document).on('click touchstart', function (e) {
    var langSwitch = document.getElementById('language-switch');
    if (!langSwitch)
      return true;

    if (langSwitch.className == 'active' || e.target.id != 'language-switch' && e.target.parentNode.id != 'language-switch')
      langSwitch.className = '';
    else
      langSwitch.className = 'active';
  });
});
