window.ParsleyConfig = window.ParsleyConfig || {};
window.ParsleyConfig.i18n = window.ParsleyConfig.i18n || {};

// Define then the messages
window.ParsleyConfig.i18n.sk = $.extend(window.ParsleyConfig.i18n.sk || {}, {
  defaultMessage: "Táto položka je neplatná.",
  type: {
    email:        "Táto položka musí byť e-mailová adresa.",
    url:          "Táto položka musí byť platná URL adresa.",
    number:       "Táto položka musí byť číslo.",
    integer:      "Táto položka musí byť celé číslo.",
    digits:       "Táto položka musí byť kladné celé číslo.",
    alphanum:     "Táto položka musí byť alfanumerická."
  },
  notblank:       "Táto položka nesmie byť prázdna.",
  required:       "Táto položka je povinná.",
  pattern:        "Táto položka je neplatná.",
  min:            "Táto položka musí byť menšia alebo rovná %s.",
  max:            "Táto položka musí byť väčšia alebo rovná %s.",
  range:          "Táto položka musí byť v rozsahu od %s do %s.",
  minlength:      "Táto položka musí mať najmenej %s znakov.",
  maxlength:      "Táto položka musí mať najviac %s znakov.",
  length:         "Táto položka musí mať dĺžku od %s do %s znakov.",
  mincheck:       "Je nutné vybrať aspoň %s možností.",
  maxcheck:       "Je nutné vybrať najviac %s možností.",
  check:          "Je nutné vybrať od %s do %s možností.",
  equalto:        "Táto položka musí byť rovnaká."
});

// If file is loaded after Parsley main file, auto-load locale
if ('undefined' !== typeof window.ParsleyValidator)
  window.ParsleyValidator.addCatalog('sk', window.ParsleyConfig.i18n.sk, true);
