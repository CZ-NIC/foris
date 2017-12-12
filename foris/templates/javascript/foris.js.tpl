Foris.messages.rErrorPassword = "{{ trans('Your password contains non-standard characters. These are not forbidden, but could cause problems on some devices.') }}";
Foris.messages.qrErrorSSID = "{{ trans('Your SSID contains non-standard characters. These are not forbidden, but could cause problems on some devices.') }}";
Foris.messages.ok = "{{ trans('OK') }}";
Foris.messages.error = "{{ trans('Error') }}";
Foris.messages.loading = "{{ trans('Loading...') }}";
Foris.messages.checkNoForward = "{{ trans('Connectivity test failed, testing connection with disabled forwarding.') }}";
Foris.messages.lanIpChanged = "{{ trans('The IP address of your router has been changed. It should be accessible from %NEW_IP_LINK%. See the note above for more information about IP address change.') }}";
Foris.messages.confirmDisabledUpdates = "{{ trans('You have chosen to not receive security updates. We strongly advice you to keep the automatic security updates enabled to receive all recommended updates for your device. Updating your router on regular basis is the only way how to ensure you will be protected against known threats that might target your home router device.\\n\\nDo you still want to continue and stay unprotected?') }}";
Foris.messages.confirmDisabledDNSSEC = "{{ trans('DNSSEC is a security technology that protects the DNS communication against attacks on the DNS infrastructure. We strongly recommend keeping DNSSEC validation enabled unless you know that you will be connecting your device in the network where DNSSEC is broken.\\n\\nDo you still want to continue and stay unprotected?') }}";
Foris.messages.confirmRestart = "{{ trans('Are you sure you want to restart the router?') }}";
Foris.messages.confirmRestartExtra = "{{ trans('\\nRemaining unread messages (%UNREAD%) will be deleted.') }}";
Foris.messages.unsavedNotificationsAlert = "{{ trans('There are some unsaved changes in the notifications settings.\\nDo you want to discard them and test the notifications with the old settings?') }}";

Foris.handleReboot = function(ips) {
  $('#rebooting-notice').show("slow");
  $('#reboot-required-notice').hide("slow");

  var port = window.location.port == "" ? "" : ":" + window.location.port;
  var ping_path = "{{ url('ping') }}"
  var urls = [window.location.protocol + "//" + window.location.hostname + port + ping_path];
  for (var i = 0; i < ips.length; i++) {
    urls.push(window.location.protocol + "//" + ips[i] + port + ping_path);
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
    Foris.waitForReachable(urls, {next: pathname}, rebootDoneCallback);
  });
};
