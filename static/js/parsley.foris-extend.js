window.ParsleyConfig = window.ParsleyConfig || {};

(function ($) {
  window.ParsleyConfig = $.extend( true, {}, window.ParsleyConfig, {
    validators: {
      foristype: function () {
        return {
          validate: function ( val, type ) {
            switch (type) {
              case 'ipv4':
                var bytes = val.split(".");
                if (bytes.length != 4)
                  return false;
                var intRE = /^[0-9]+$/;
                for (var i = 0; i < bytes.length; i++) {
                  // check it's an integer number, not exponential format, hex number etc...
                  if (!intRE.test(bytes[i]))
                    return false;
                  if (bytes[i] < 0 || bytes[i] > 255)
                    return false;
                }
                return true;
              case 'ipv6':
                // TODO: implement validator
                return true;
              case 'ipv6prefix':
                // TODO: implement validator
                return true;
              case 'macaddress':
                // TODO: implement validator
                return true;
              default:
                return false;
            }
          }
          , priority: 32
        }
      }
    },
    messages: {
      foristype: {
        ipv4: "This is not a valid IPv4 address.",
        ipv6: "This is not a valid IPv6 address.",
        ipv6prefix: "This is not a valid IPv6 prefix.",
        macaddress: "This is not a valid MAC address."
      }
    }
  });
}(window.jQuery || window.Zepto));
