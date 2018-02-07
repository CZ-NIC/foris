window.ParsleyValidator
    .addValidator('bytelength', function ( value, arrayRange ) {
        var byteLength = encodeURI(value).replace(/%../g, "?").length;
        return byteLength >= arrayRange[0] && byteLength <= arrayRange[1];
      }, 32)
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
          case 'domain':
            regExp = /^([a-zA-Z0-9-]{1,63}\.?)*$/g;
            break;
          case 'datetime':
            return Date.parse(val) ? true : false;
          default:
              console.dir(window.ParsleyValidator.validators.type(type));
            return window.ParsleyValidator.validators.type(type);
        }

        return val !== '' ? regExp.test(val) : false;
    }, 32);

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
