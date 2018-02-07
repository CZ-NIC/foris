window.ParsleyConfig = window.ParsleyConfig || {};
window.ParsleyConfig.i18n = window.ParsleyConfig.i18n || {};

// Define then the messages
window.ParsleyConfig.i18n.{{ lang() }} = $.extend(window.ParsleyConfig.i18n.{{ lang() }} || {}, {
  defaultMessage: '{{ trans("This value seems to be invalid.") }}',
  type: {
    email:        '{{ trans("This value should be a valid email.") }}',
    url:          '{{ trans("This value should be a valid url.") }}',
    number:       '{{ trans("This value should be a valid number.") }}',
    integer:      '{{ trans("This value should be a valid integer.") }}',
    digits:       '{{ trans("This value should be digits.") }}',
    alphanum:     '{{ trans("This value should be alphanumeric.") }}'
  },
  notblank:       '{{ trans("This value should not be blank.") }}',
  required:       '{{ trans("This value is required.") }}',
  pattern:        '{{ trans("This value seems to be invalid.") }}',
  min:            '{{ trans("This value should be greater than or equal to %s.") }}',
  max:            '{{ trans("This value should be lower than or equal to %s.") }}',
  range:          '{{ trans("This value should be between %s and %s.") }}',
  minlength:      '{{ trans("This value is too short. It should have %s characters or more.") }}',
  maxlength:      '{{ trans("This value is too long. It should have %s characters or fewer.") }}',
  length:         '{{ trans("This value length is invalid. It should be between %s and %s characters long.") }}',
  mincheck:       '{{ trans("You must select at least %s choices.") }}',
  maxcheck:       '{{ trans("You must select %s choices or fewer.") }}',
  check:          '{{ trans("You must select between %s and %s choices.") }}',
  equalto:        '{{ trans("This value should be the same.") }}',
  bytelength:     '{{ trans("This value length is invalid. It should be between %s and %s characters long.") }}',
  extratype: {
    ipv4:         '{{ trans("This is not a valid IPv4 address.") }}',
    ipv4netmask:  '{{ trans("This is not a valid IPv4 netmask.") }}',
    ipv4prefix:   '{{ trans("This is not a valid IPv4 prefix.") }}',
    ipv6:         '{{ trans("This is not an IPv6 address with prefix length.") }}',
    anyip:        '{{ trans("This is not a valid IPv4 or IPv6 address.") }}',
    ipv6prefix:   '{{ trans("This is not a valid IPv6 prefix.") }}',
    macaddress:   '{{ trans("This is not a valid MAC address.") }}',
    domain:       '{{ trans("This is not a valid domain name.") }}',
    datetime:     '{{ trans("This is not a valid time (YYYY-MM-DD HH:MM:SS).") }}'
  }
});

// If file is loaded after Parsley main file, auto-load locale
if ('undefined' !== typeof window.ParsleyValidator)
  window.ParsleyValidator.addCatalog('{{ lang() }}', window.ParsleyConfig.i18n.{{ lang() }}, true);
