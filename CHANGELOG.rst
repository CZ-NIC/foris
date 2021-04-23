101.1.2 (2021-04-23)
--------------------

* change default path of ubus.sock to be aligned with changes in OpenWrt 21.02
* remove unused requirements.txt

101.1.1 (2021-01-12)
--------------------

* html escape next in login template

101.1 (2020-07-16)
------------------

* wifi: add 802.11ac 160 Mhz wide channel

101.0 (2020-06-19)
----------------

* add ability to create external links in menu
* internal redirect from foris pages
* wan: make pppoe password hidden by default
* update translations

100.7 (2020-01-09)
------------------

* time: fix storing of three-level names timezones

100.6 (2019-10-17)
------------------

* about: show Turris OS version or branch in about tab

100.5 (2019-09-28)
------------------

* translations updated

100.4 (2019-09-10)
------------------

* translations updated
* maintenance: add placeholder for 'Sender address and 'Server address'
* maintenance: Generate testing notification as an error

100.3 (2019-07-25)
------------------

* wan: make PPPoE credentials mandatory

100.2 (2019-07-17)
------------------

* fix english typos
* guest: disabeling fix

100.1 (2019-07-10)
------------------

* translations updated
* remote: fix non-clickable buttons in Chrome
* lan+guest: check whether Router IP is not within DHCP range
* time: show Time settings during initial configuration
* updater: show only 'Save' when updater is disabled

100.0 (2019-05-27)
------------------

* translations updated
* wifi: don't allow to set the same band for different wifi cards
* update: alert text fix

99.10 (2019-05-02)
------------------

* translations updated
* updater: change approval delay from hours(int) to days(float)
* updater: user entry points to determine whether updater can be disabled
* updater: user-list UI update
* wan: better no link message
* wan: convert initial 'none' protocol to 'dhcp'

99.9 (2019-04-29)
-----------------

* about: remove board_name field
* lan+guest: dhcp leases display fix
* translations updated
* guide: finished text updated

99.8 (2019-04-05)
-----------------

* add sentry indicator to global state
* handle lighttpd restarts
* menu: display steps fix

99.7.5 (2019-04-03)
-------------------

* sentry integration
* plugin import fix

99.7.4 (2019-04-03)
-------------------

* setup.py: missing package fix

99.7.3 (2019-04-02)
-------------------

* wifi: added enable_guest option to wifi form (without this option it is not possible to set wifi)
* maintain: disappearing zero in automatic restarts form fix
* updater: api changes - enabled() can have tree states now
* refactoring: config pages splitted into separate modules
* disable WS filtering when controller-id is not set (fixes fitler notifications from ubus)
* second level menus implemented
* remote: description updated
* subordiantes: moved to a separate plugin

99.7.2 (2019-03-13)
-------------------

* wifi: backend api changed

99.7.1 (2019-03-12)
-------------------

* translations: small fixes
* subordinates: small ui fixes

99.7 (2019-03-08)
-----------------

* translations updated
* ui improvements: new spinner using css and fontawesome
* subordinates tab added

99.6.1 (2019-02-18)
-------------------

* controller id fix for non-mqtt buses

99.6 (2019-02-14)
-----------------

* mqtt: allow to set controller id

99.5 (2019-02-11)
-----------------

* password: display how many times was the compromised password used
* translations updates
* small locale fixes

99.4 (2019-01-31)
-----------------

* mqtt: can set path to credentials file

99.3.2 (2019-01-30)
------------------

* translations updated
* guide uix improvements 2

99.3.1 (2019-01-29)
------------------

* sass compile fix
* guide uix improvements

99.3 (2019-01-29)
-----------------

* new logo integrated
* branding removed
* updater api updated

99.2 (2019-01-16)
-----------------

* mqtt add a proper timeout
* remote tab added
* js vex translations

99.1 (2018-12-27)
-----------------

* small sass/css updates
* mqtt bus fixes
* translations updated

99.0 (2018-12-21)
-----------------

* support for mqtt message bus
* translations updated

98.19.1 (2018-12-05)
--------------------

* missing file fix

98.19 (2018-12-05)
------------------

* lan,wan,guest: interface up/down handling
* networks: ssid for wifis + icon change on click
* lan: modes renamed

98.18 (2018-11-30)
------------------

* setup.py: PEP508
* networks: api updates and cleanups
* translations updated

98.17 (2018-11-08)
------------------

* networks: new API + display wifi interfaces
* maintain: validation of email recp list
* guest+lan: dhcp range verification

98.16 (2018-10-29)
------------------

* Norwegian Bokmål lanugage added
* time: display a list of ntp servers

98.15 (2018-10-25)
------------------

* huge translations update
* guide: show worflow title
* contract related ifs and conditionals removed
* text updates

98.14.1 (2018-10-24)
--------------------

* import fix

98.14 (2018-10-23)
------------------

* dns: ability to set custom forwarders added
* removing data_collect (will be a part of a separete plugin)

98.13 (2018-10-16)
------------------

* lan+wan+guest tab will display a warning when it doens't have any interface assigned
* lan+guest tab show a list of dhcp clients
* web tab contains a new 'Local Server' workflow
* LAN can be set to unmanaged mode
* networks tab will display more detail of network interfaces

98.12 (2018-09-26)
------------------

* text updates
* merged translations from weblate

98.11 (2018-09-21)
------------------

* dhcp lease time option added to LAN and guest tabs

98.10 (2018-09-20)
------------------

* config menu refactoring
* added reset guide button to guide
* profile tab added (only for turris-os-version >= 4.0 and mox/omnia only)
* new modal dialogs using js library vex
* new spinner for restarts and reboots
* lan tab splitted to lan and guest tabs
* networks tab added (only for turris-os-version >= 4.0 and mox/omnia only)
* fixing reboot confirms

98.9 (2018-08-29)
-----------------

* mox branding added

98.8 (2018-08-29)
-----------------

* password and administration tab merged
* wifi tab show message fix

98.7 (2018-08-16)
-----------------

* session fix

98.6 (2018-08-16)
-----------------

* python3 compatibility
* jinja2 and ws fix

98.5 (2018-08-09)
-----------------

* version printing
* using console scripts in entry points

98.4 (2018-06-29)
-----------------

* CHANGELOG file added
* new plugin system integrated
