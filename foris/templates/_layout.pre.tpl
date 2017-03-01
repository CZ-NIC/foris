%# Foris - web administration interface for OpenWrt based on NETCONF
%# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
%#
%# This program is free software: you can redistribute it and/or modify
%# it under the terms of the GNU General Public License as published by
%# the Free Software Foundation, either version 3 of the License, or
%# (at your option) any later version.
%#
%# This program is distributed in the hope that it will be useful,
%# but WITHOUT ANY WARRANTY; without even the implied warranty of
%# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%# GNU General Public License for more details.
%#
%# You should have received a copy of the GNU General Public License
%# along with this program.  If not, see <http://www.gnu.org/licenses/>.
%#
<!DOCTYPE html>
<html lang="{{ lang() }}">
<head>
    <meta charset="utf-8">
    <title>{{ title + " | " if defined('title') else "" }}{{ trans("Turris router administration interface") }}</title>
    <!--[if gt IE 8]><!--><link href="{{ static("css/screen.css") }}?md5=MD5SUM" rel="stylesheet" media="screen"><!--<![endif]-->
    <!--[if lt IE 9]>
        <script src="{{ static("js/contrib/html5.js") }}"></script>
        <link href="{{ static("css/ie8.css") }}?md5=MD5SUM" rel="stylesheet" media="screen">
    <![endif]-->
    %if defined('PLUGIN_STYLES') and PLUGIN_STYLES:
      %for static_filename in PLUGIN_STYLES:
        <link href="{{ "/plugins/" + PLUGIN_NAME }}{{ static(static_filename) }}" rel="stylesheet" media="screen">
      %end
    %end
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="{{ static("js/contrib/jquery.min.js") }}"></script>
    <script src="{{ static("js/contrib/parsley.min.js") }}"></script>
    <script src="{{ static("js/parsley.foris-extend.min.js") }}?md5=MD5SUM"></script>
    <script src="{{ static("js/foris.min.js") }}?md5=MD5SUM"></script>
    <script src="{{ url("translate_js", filename="foris.js") }}?md5={{ trans_js_md5('foris.js') }}"></script>
    <script src="{{ url("translate_js", filename="parsley.messages.js") }}?md5={{ trans_js_md5('parsley.messages.js') }}"></script>
</head>
<body>
    {{! base }}
</body>
</html>
