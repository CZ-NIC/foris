window.ParsleyValidator
    .addValidator('bytelength', function ( value, arrayRange ) {
        var byteLength = encodeURI(value).replace(/%../g, "?").length;
        return byteLength >= arrayRange[0] && byteLength <= arrayRange[1];
      }, 32)
    .addMessage('cs', 'bytelength', "Tato položka musí mít délku od %s do %s znaků.")
    .addMessage('de', 'bytelength', "Die Länge des Eingabewerts muss zwischen %s bis %s Zeichen sein.")
    .addMessage('en', 'bytelength', "This value length is invalid. It should be between %s and %s characters long.")
    .addValidator('extratype', function( val, type ) {
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
        var isIPv4Prefix = function(val) {
            var splitVal = val.split("/");
            if (splitVal.length != 2) return false;
            if (!splitVal[1].match(/^\d+$/)) return false;
            var prefix = parseInt(splitVal[1], 10);
            if (!isIPv4(splitVal[0]) || prefix < 0 || prefix > 32) return false;
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
          case 'ipv4prefix':
            if (isIPv4Prefix(val))
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
              console.dir(window.ParsleyValidator.validators.type(type));
            return window.ParsleyValidator.validators.type(type);
            //return false;
        }

        return val !== '' ? regExp.test(val) : false;
    }, 32)
    .addMessage('cs', 'extratype', {
      ipv4: "Toto není platná IPv4 adresa.",
      ipv4netmask: "Toto není platná IPv4 síťová maska.",
      ipv4prefix: "Toto není IPv4 adresa s délkou prefixu.",
      ipv6: "Toto není platná IPv6 adresa.",
      anyip: "Toto není platná IPv4 nebo IPv6 adresa.",
      ipv6prefix: "Toto není IPv6 adresa s délkou prefixu.",
      macaddress: "Toto není platná MAC adresa."
    })
    .addMessage('de', 'extratype', {
      ipv4: "Dies ist keine gültige IPv4-Adresse.",
      ipv4netmask: "Dies ist keine gültige IPv4-Netzmaske.",
      ipv4prefix: "Dies ist keine IPv4-Adresse mit einer Präfixlänge.",
      ipv6: "Dies ist keine gültige IPv6-Adresse.",
      anyip: "Dies ist keine gültige IPv4- oder IPv6-Adresse.",
      ipv6prefix: "Dies ist keine IPv6-Adresse mit einer Präfixlänge.",
      macaddress: "Dies ist keine gültige MAC-Adresse."
    })
    .addMessage('en', 'extratype', {
      ipv4: "This is not a valid IPv4 address.",
      ipv4netmask: "This is not a valid IPv4 netmask.",
      ipv4prefix: "This is not a valid IPv4 prefix.",
      ipv6: "This is not an IPv6 address with prefix length.",
      anyip: "This is not a valid IPv4 or IPv6 address.",
      ipv6prefix: "This is not a valid IPv6 prefix.",
      macaddress: "This is not a valid MAC address."
    });

// patch method for getting error messages so it can get extratype messages from object structure
window.ParsleyValidator.getErrorMessage = function(constraint) {
  var message;
  // Type constraints are a bit different, we have to match their requirements too to find right error message
  if ('type' === constraint.name || 'extratype' === constraint.name)
    message = this.catalog[this.locale][constraint.name][constraint.requirements];
  else
    message = this.formatMessage(this.catalog[this.locale][constraint.name], constraint.requirements);
  return '' !== message ? message : this.catalog[this.locale].defaultMessage;
};
