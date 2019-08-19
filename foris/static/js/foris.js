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
    input.parent().append(' <i class="fas fa-spinner rotate"></i>');
    Foris.updateForm(input.closest("form"));
  });

  Foris.initParsley();
  Foris.initPasswordHiding();
  Foris.initClickableHints();
  Foris.initSmoothScrolling();
  Foris.applySVGFallback();
  Foris.initWsHandlers();
  Foris.initWebsockets();
  Foris.initRebootRequired();
  Foris.initMenuExpand();
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

Foris.WsHandlers = {};

Foris.addWsHanlder = (module, handler, controller_id) => {
    controller_id = controller_id || $('meta[name=controller-id]').attr("content") || '+';
    let moduleHandler = Foris.WsHandlers[module] || {};
    let handlers = moduleHandler[controller_id] || [];
    handlers.push(handler);
    moduleHandler[controller_id] = handlers;
    Foris.WsHandlers[module] = moduleHandler;
};

Foris.initWsHandlers = () => {
    Foris.addWsHanlder("maintain", (msg) => {
        switch (msg.action) {
            case "reboot":
                Foris.handleReboot(msg.data.ips, msg.data.remains);
                break;
            case "reboot_required":
                $('#reboot-required-notice').show("slow");
                break;;
            case "network-restart":
                Foris.handleNetworkRestart(msg.data.ips, msg.data.remains);
                break;
            case "lighttpd-restart":
                Foris.handleForisRestart(msg.data.remains);
                break;
        }
    });

    Foris.addWsHanlder("router_notifications", (msg) => {
        if (msg.action == "create" || msg.action == "mark_as_displayed") {
            Foris.handleNotificationsCountUpdate(msg.data.new_count);
        }
    });

    Foris.addWsHanlder("updater", (msg) => {
        if (msg.action == "run") {
            Foris.handleUpdaterRun(msg.data.status != "exit" && msg.data.status != "failed");
        }
    });
};

Foris.initWebsockets = function() {

  var protocol = window.location.protocol == "http:" ? "ws" : "wss";
  var path = $('meta[name=foris-' + protocol + '-path]').attr("content");
  var port = $('meta[name=foris-' + protocol + '-port]').attr("content");
  path = path ? path : "/foris-ws";
  port = port ? ":" + port : (window.location.port == "" ? "" : ":" + window.location.port);
  var url = protocol + "://" + window.location.hostname + port + path;

  // Connect to foris-ws
  ws = new WebSocket(url);

  ws.onopen = function () {
    var output = JSON.stringify({"action": "subscribe", "params": Object.keys(Foris.WsHandlers)});
    ws.send(output);
    console.log("WS registering for: " + Object.keys(Foris.WsHandlers));
  };

  ws.onmessage = function (e) {
    console.log("WS message received: " + e.data);
    var parsed = JSON.parse(e.data);
    if (Foris.WsHandlers.hasOwnProperty(parsed.module)) {
      // filter using controller_id
      for (let key in Foris.WsHandlers[parsed.module]) {
        if (key == parsed.controller_id || key == "+") {  // '+' means perform every time
          for (let action of Foris.WsHandlers[parsed.module][key]) {
              action(parsed);
          }
        }
      }
    }
  };

  ws.onerror = function(e) {
    console.log("WS error occured:" + e);
  };

  ws.onclose = function() {
    console.log("WS connection closed.");
  };

};

Foris.initPasswordHiding = function() {
    $(".password-toggle").click(function () {
        var input= $(this).prev();
        if (input.attr("type") == "password") {
            input.attr("type", "text");
            $(this).find("i").attr("class", "fas fa-eye-slash");
        } else {
            input.attr("type", "password");
            $(this).find("i").attr("class", "fas fa-eye");
        }
    })
}

Foris.afterAjaxUpdateFunctions = [];
Foris.afterAjaxUpdate = function(response, status, xhr) {
  for (let afterFunction of Foris.afterAjaxUpdateFunctions) {
      afterFunction(response, status, xhr);
  }
}

Foris.updateForm = function (form) {
  var serialized = form.serializeArray();
  serialized.push({name: '_update', value: '1'});

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
    Foris.initParsley(response, status, xhr);
    Foris.initPasswordHiding(response, status, xhr);
    Foris.afterAjaxUpdate(response, status, xhr);
    Foris.initClicksQR(response, status, xhr);
    $(document).trigger('formupdate', [form]);
  });
  form.find("input, select, button").attr("disabled", "disabled");
};

Foris.confirmDialog = function (...vexArgs) {
    vex.dialog.buttons.YES.text = Foris.messages.vexYes;
    vex.dialog.buttons.NO.text = Foris.messages.vexNo;
    vex.dialog.confirm(...vexArgs);
};

Foris.initEulaForm = function () {
  $("#updater-eula").show();

  $('#field-agreed_0').click(function () {
    Foris.confirmDialog(
        {
            unsafeMessage: Foris.messages.confirmDisabledUpdates,
            callback: (value) => {
                if (value) {
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
                }
            }
        }
    );
  });

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

Foris.updateWiFiQR = function (radio, ssid, password, hidden, guest) {
  var escape = function(field) {
    // content of the field should be properly escaped see
    // https://github.com/zxing/zxing/wiki/Barcode-Contents#wifi-network-config-android

    // add quotes if it can be interpreted as hex
    if (/^[0-9a-fA-F]+$/.test(field)) {
        return '"' + field + '"';
    }

    // escape characters " ; , : \
    field = field.replace(/\\/, '\\\\');
    field = field.replace(/"/, '\\"');
    field = field.replace(/;/, '\\;');
    field = field.replace(/,/, '\\,');
    field = field.replace(/:/, '\\:');

    return field;
  }
  var codeElement = $((guest ? "#wifi-qr-guest-":"#wifi-qr-") + radio);
  codeElement.empty();

  if (guest) {
    if (!$("#field-" + radio + "-guest_enabled_1").prop("checked"))
      return;
  } else {
    if (!$("#field-" + radio + "-device_enabled_1").prop("checked"))
      return;
  }

  $(".qr-error-" + radio + "-" + (guest ? "guest-": "")).remove();
  var showQRError = function (message, id) {
    $("#" + id).parent().append("<div class=\"message warning row qr-error-" + radio + "-" + (guest ? "guest-": "") + "\">" + message + "</div>");
  };

  var passed = true;
  if (!Foris.checkLowerAsciiString(ssid)) {
    showQRError(Foris.messages.qrErrorSSID, "field-" + radio + (guest ? "-guest_" : "-") + "ssid");
    passed = false;
  }
  if (!Foris.checkLowerAsciiString(password)) {
    showQRError(Foris.messages.qrErrorPassword, "field-" + radio + (guest ? "-guest_" : "-") + "password");
    passed = false;
  }

  if (!passed)
    return;

  if (hidden)
    hidden = 'H:true';
  else
    hidden = '';

  codeElement.empty().qrcode({
    size: 200,
    text: 'WIFI:T:WPA;S:' + escape(ssid) + ';P:' + escape(password) + ';' + hidden + ';'
  });
};

Foris.initClicksQR = function () {
  $(".wifi-qr img").on("click", function(e) {
    e.preventDefault();
    $(this).parent().find(".wifi-qr-box").toggle("normal");
    $(this).toggle("normal");
  });
  $(".wifi-qr-box").on("click", function(e) {
    e.preventDefault();
    $(this).parent().find("img").toggle("normal");
    $(this).toggle("normal");
  });
}

Foris.initWiFiQR = function () {
  // NOTE: make sure that jquery.qrcode is loaded on the page that's using
  // this method. Alternatively, it could be loaded using $.getScript() here.

  // determine present radios from wifi-enable checkboxes

  Foris.initClicksQR();

  var radios = [];
  $("input[id$='-device_enabled_1']").each(function (i, el) {
    radios.push(el.getAttribute('id').replace(/field-(radio\d+)-.*/, '$1'));
  });

  var doRender = function (radio) {
    doRender.debounceTimeout = null;

    Foris.updateWiFiQR(
        radio,
        $('#field-' + radio + '-ssid').val(),
        $('#field-' + radio + '-password').val(),
        $('#field-' + radio + '-ssid_hidden_1').prop('checked'),
        false
    );
    Foris.updateWiFiQR(
        radio,
        $('#field-' + radio + '-guest_ssid').val(),
        $('#field-' + radio + '-guest_password').val(),
        false,
        true
    );
  };

  for (var i=0; i < radios.length; i++) {
    var radio = radios[i];

    doRender(radio);

    $(document).on('change keyup paste',
        '#field-' + radio + '-ssid, ' +
        '#field-' + radio + '-password, ' +
        '#field-' + radio + '-guest_ssid, ' +
        '#field-' + radio + '-guest_password, ' +
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
  $(".notification.action_needed a").on("click", function(e) {
    e.preventDefault();
    var id = $(this).data("id");
    $.post(Foris.scriptname + "/main/notifications/ajax",
        {
          action: "trigger-action",
          notification_id: id,
          csrf_token: csrf_token
        },
        function(data) {
          if (data.success) {
            //for (var i=0; i < data.displayedIDs.length; i++) {
            //  $("#notification_" + data.displayedIDs[i]).fadeOut(800);
            //}
          }
        }
    );
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

  $(document).on("click", "#notifications-test", function (e) {
    if (showNotificationTestAlert) {
      e.preventDefault();
      vex.dialog.buttons.YES.text = Foris.messages.vexYes;
      vex.dialog.buttons.NO.text = Foris.messages.vexNo;
      Foris.confirmDialog({
          unsafeMessage: Foris.messages.unsavedNotificationsAlert,
          callback: (value) => value && $("#notifications-form")[0].reset()
      });
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

Foris.waitForUnreachable = function(url, callback, timeout, retries=-1) {
  var timeout = timeout || 1000;
  // wait till current address is available
  var url = url;
  let local_retries = retries;
  var unreachableFunction = function() {
    $.ajax({
      url: url,
      type: "GET",
      async: true,
      data: {silent: true},
      crossDomain: true,
      headers: {'X-Requested-With': 'XMLHttpRequest'},
      success: function(data, text, jqXHR) {
        if (Math.round(local_retries) != 0) {
          setTimeout(unreachableFunction, timeout);
        }
        local_retries -= 1;
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

Foris.handleReboot = async function(ips, time, step=0.1) {
  if (Foris.SpinnerIsShown()) {
    return; // already running
  }
  for (i = time / 1000; i >= 0; i = Math.round((i - step) * 100) / 100) {
    await Foris.TimeoutPromiss((left) => Foris.SpinnerDisplay(Foris.messages.rebootIn(left)), step, i);
  }
  await Foris.TimeoutPromiss(() => Foris.SpinnerDisplay(Foris.messages.rebootTriggered), 1);

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
    Foris.SpinnerDisplay(Foris.messages.tryingToReconnect);
    Foris.waitForReachable(urls, {next: pathname}, rebootDoneCallback, 5000);
  });
};

Foris.handleNetworkRestart = async function(ips, time, step=0.1) {
  if (Foris.SpinnerIsShown()) {
    return; // already running
  }
  for (i = time / 1000; i >= 0; i = Math.round((i - step) * 100) / 100) {
    await Foris.TimeoutPromiss((left) => Foris.SpinnerDisplay(Foris.messages.networkRestartIn(left)), step, i);
  }
  await Foris.TimeoutPromiss(() => Foris.SpinnerDisplay(Foris.messages.networkRestartTriggered), 1);

  var port = window.location.port == "" ? "" : ":" + window.location.port;
  var protocol = window.location.protocol;
  var pathname = window.location.pathname;
  var search = window.location.search;
  var urls = [window.location.protocol + "//" + window.location.hostname + port + Foris.pingPath];
  for (var i = 0; i < ips.length; i++) {
    urls.push(window.location.protocol + "//" + ips[i] + port + Foris.pingPath);
  }

  var restartLanDoneCallback = function(url, jqXHR) {
    if (jqXHR.status == 0) {
        return false;
    }
    if (jqXHR.status == 200) {
        if (jqXHR.responseJSON && jqXHR.responseJSON.loginUrl) {
            window.location = jqXHR.responseJSON.loginUrl;
        }
    }
  }

  // start the machinery
  Foris.waitForUnreachable(window.location.pathname, function (xhr, text, error) {
    var pathname = window.location.pathname;
    Foris.SpinnerDisplay(Foris.messages.tryingToReconnect);
    Foris.waitForReachable(urls, {next: pathname}, restartLanDoneCallback, 2000);
  }, 5);
};

Foris.handleForisRestart = async function(time, step=0.1) {
  if (Foris.SpinnerIsShown()) {
    return; // already running
  }
  for (i = time / 1000; i >= 0; i = Math.round((i - step) * 100) / 100) {
    await Foris.TimeoutPromiss((left) => Foris.SpinnerDisplay(Foris.messages.forisRestartIn(left)), step, i);
  }
  await Foris.TimeoutPromiss(() => Foris.SpinnerDisplay(Foris.messages.forisRestartTriggered), 1);

  var port = window.location.port == "" ? "" : ":" + window.location.port;
  var protocol = window.location.protocol;
  var pathname = window.location.pathname;
  var search = window.location.search;
  var urls = [window.location.protocol + "//" + window.location.hostname + port + Foris.pingPath];

  var restartLanDoneCallback = function(url, jqXHR) {
    if (jqXHR.status == 0) {
        return false;
    }
    if (jqXHR.status == 200) {
        if (jqXHR.responseJSON && jqXHR.responseJSON.loginUrl) {
            window.location = jqXHR.responseJSON.loginUrl;
        }
    }
  }

  // start the machinery
  Foris.waitForUnreachable(window.location.pathname, function (xhr, text, error) {
    var pathname = window.location.pathname;
    Foris.SpinnerDisplay(Foris.messages.tryingToReconnect);
    Foris.waitForReachable(urls, {next: pathname}, restartLanDoneCallback, 2000);
  }, 5);
};

Foris.handleNotificationsCountUpdate = function(new_count) {
  var old_count = parseInt($("#notifications_menu_tag").text());
  $("#notifications_menu_tag").text(new_count);
  if (new_count > 0) {
    if (old_count > 0) {
      // blink
      $("#notifications_menu_tag").addClass("bounce");
    } else {
      // show
      $("#notifications_menu_tag").show();
      $("#notifications_menu_tag").addClass("bounce");
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

Foris.SpinnerIsShown = function() {
    return $("#foris-spinner-frame").length > 0
};

Foris.SpinnerDisplay = function(text) {
    if (Foris.SpinnerIsShown()) {
        $("#foris-spinner-text").html(text);
    } else {
        $("body").append(`<div id="foris-spinner-frame"><div id="foris-spinner"></div><div id="foris-spinner-text">${text}</div></div>`);
    }
};

Foris.SpinnerRemove = function() {
    $("#foris-spinner-frame").remove();
};

Foris.TimeoutPromiss = function(handler, timeout, data) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            handler(data);
            resolve();
        }, timeout * 1000);
    });
};

Foris.clearNetworkWarnings = function(network_name, data) {
    if (data.network == network_name && data.action == "ifup") {
        $("#no-interface-up-warning").hide("slow");
    }
}

Foris.performBackendQuery = async (controller_id, module, action, data) => {
    let csrf = $('meta[name=csrf]').prop("content");
    let output = {
        module: module,
        kind: "request",
        action: action,
    };
    if (controller_id) {
        output.controller_id = controller_id;
    }
    if (data) {
        output.data = JSON.stringify(data);
    }
    output.csrf_token = csrf;
    return await $.ajax({
        type: "POST",
        url: Foris.backendPath,
        dataType: "json",
        data: output,
    });
};

Foris.initMenuExpand = () => {
    $("#menu nav li.nav-expandable").click((e) => {
        e.preventDefault();
        let current = $(e.currentTarget);
        let self_slug = current.attr("data-self-name");
        if (self_slug && !current.hasClass("subpage-active")) {
            $(`.parent-name-${self_slug}`).toggle("slow");
            let expand_tag = current.find(".expand-tag i");
            if (expand_tag.hasClass("fa-caret-square-down")) {
                expand_tag.removeClass();
                expand_tag.addClass("fas fa-caret-square-up");
            } else {
                expand_tag.removeClass();
                expand_tag.addClass("fas fa-caret-square-down");
            }
        }
    });
}

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

  // init modal dialogs
  vex.defaultOptions.className = 'vex-theme-top';
  vex.defaultOptions.overlayClosesOnClick = false;
});
