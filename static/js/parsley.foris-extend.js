window.ParsleyConfig = window.ParsleyConfig || {};

(function ($) {
  window.ParsleyConfig = $.extend( true, {}, window.ParsleyConfig, {
    validators: {
      extratype: function () {
        return {
          validate: function ( val, type ) {
            var regExp;
            var isIPv4 = function(val) {
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
            };
            var isIPv4Netmask = function(val) {
              var bytes = val.split(".");
              if (bytes.length != 4)
                return false;
              var intRE = /^[0-9]+$/;
              var was_zero = false;
              for (var i = 0; i < bytes.length; i++) {
                // check it's an integer number, not exponential format, hex number etc...
                if (!intRE.test(bytes[i]))
                  return false;
                if (bytes[i] < 0 || bytes[i] > 255)
                  return false;
                for (var j = 7; j >= 0; j--) {
                  if ((bytes[i] & 1 << j) == 0) {
                    was_zero = true;
                  } else if (was_zero) {
                    // 1 and we have seen zero already
                    return false;
                  }
                }
              }
              return true;
            };
            switch (type) {
              case 'ipv4':
                return isIPv4(val);
              case 'ipv4netmask':
                return isIPv4Netmask(val);
              case 'anyip':
                if (isIPv4(val))
                  return true;
                // else fall through to ipv6
              case 'ipv6':
                // source: http://home.deds.nl/~aeron/regex/
                regExp = /^((?=.*::)(?!.*::.+::)(::)?([\dA-F]{1,4}:(:|\b)|){5}|([\dA-F]{1,4}:){6})((([\dA-F]{1,4}((?!\3)::|:\b|$))|(?!\2\3)){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})$/i;
                break;
              case 'ipv6prefix':
                // source: http://home.deds.nl/~aeron/regex/
                regExp = /^((?=.*::)(?!.*::.+::)(::)?([\dA-F]{1,4}:(:|\b)|){5}|([\dA-F]{1,4}:){6})((([\dA-F]{1,4}((?!\3)::|:\b|$))|(?!\2\3)){2}|(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4})$/i;
                var splitVal = val.split("/");
                if (splitVal.length != 2) return false;
                if (!/^(\d|[1-9]\d|1[0-1]\d|12[0-8])$/.test(splitVal[1])) return false;
                val = splitVal[0];
                break;
              case 'macaddress':
                regExp = /^([0-9A-F]{2}:){5}([0-9A-F]{2})$/i;
                break;
              default:
                return false;
            }

            return val !== '' ? regExp.test(val) : false;
          }
          , priority: 32
        }
      }
      , byterangelength: function () {
        return {
          validate: function ( val, arrayRange ) {
            var byteLength = encodeURI(val).replace(/%../g, "?").length;
            return byteLength >= arrayRange[0] && byteLength <= arrayRange[1];
          }
          , priority: 32
        }
      }
    },
    messages: {
      extratype: {
        ipv4: "This is not a valid IPv4 address.",
        ipv4netmask: "This is not a valid IPv4 netmask.",
        ipv6: "This is not an IPv6 address with prefix length.",
        anyip: "This is not a valid IPv4 or IPv6 address.",
        ipv6prefix: "This is not a valid IPv6 prefix.",
        macaddress: "This is not a valid MAC address."
      }
      , byterangelength: "This value length is invalid. It should be between %s and %s characters long."
    }
  });
}(window.jQuery || window.Zepto));
