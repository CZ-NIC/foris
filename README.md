Foris
======

Foris is Remote Uci - it is a web GUI for configuration of system via Nuci,
i.e. Using Netconf.

Nowadays, Foris is in early stage of development and almost everything in it
is a possible subject to change, thus there's no guaranteed API stability
and all the parts should be used externally only with extreme caution, if ever...


Internal redirects to reForis
-----------------------------

Redirects from Foris page to reForis page.

Redirects are defined in `*.csv` files inside `/usr/share/foris/reforis-links/`.
File have two columns - `from url` and `to url`.

Requested url's path ending is checked and if it matches a first column,
message is displayed with a link to the second column's url.

For example:
```
"/config/my-plugin/","/reforis/my-plugin"
```

Note that:
* trailing slash in first column is important for successful matching
* `*.csv` files should be a part of the reforis or reforis plugin package (so the message is displayed only if target is present).

External links
--------------

Redirects from Foris menu to external link.

Redirects are defined in `*.csv` files inside `usr/share/foris/external-links/`.
The file have up to four columns - page slug, menu title, target url and menu item order (optional).

For example:
```
"openvpn-client","OpenVPN client","/reforis/openvpn-client/",
"sentinel","Sentinel","/reforis/sentinel/",30
```
