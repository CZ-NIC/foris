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
    <link rel="shortcut icon" href="{{ static("img/favicon.ico") }}">
    %if defined('PLUGIN_STYLES') and PLUGIN_STYLES:
      %for static_filename in PLUGIN_STYLES:
        <link href="{{ static("plugins/%s/%s" % (PLUGIN_NAME, static_filename)) }}" rel="stylesheet" media="screen">
      %end
    %end
    <link href="{{ static("css/fa-regular.min.css") }}" rel="stylesheet" media="screen">
    <link href="{{ static("css/fa-solid.min.css") }}" rel="stylesheet" media="screen">
    <link href="{{ static("css/fontawesome.min.css") }}" rel="stylesheet" media="screen">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    % if foris_info.websockets["ws_port"]:
    <meta name="foris-ws-port" content="{{ str(foris_info.websockets["ws_port"]) }}">
    % end
    % if foris_info.websockets["ws_path"]:
    <meta name="foris-ws-path" content="{{ foris_info.websockets["ws_path"] }}">
    % end
    % if foris_info.websockets["wss_port"]:
    <meta name="foris-wss-port" content="{{ str(foris_info.websockets["wss_port"]) }}">
    % end
    % if foris_info.websockets["wss_path"]:
    <meta name="foris-wss-path" content="{{ foris_info.websockets["wss_path"] }}">
    % end
    <script src="{{ static("js/contrib/jquery.min.js") }}"></script>
    <script src="{{ static("js/contrib/parsley.min.js") }}"></script>
    <script src="{{ static("js/parsley.foris-extend.min.js") }}?md5=MD5SUM"></script>
    <script src="{{ static("js/foris.min.js") }}?md5=MD5SUM"></script>
    <script src="{{ url("render_js", filename="foris.js") }}?md5={{ js_md5('foris.js') }}"></script>
    <script src="{{ url("render_js", filename="parsley.messages.js") }}?md5={{ js_md5('parsley.messages.js') }}"></script>
    %if defined('PLUGIN_STATIC_SCRIPTS') and PLUGIN_STATIC_SCRIPTS:
      %for static_filename in PLUGIN_STATIC_SCRIPTS:
        <script src="{{ static("plugins/%s/%s" % (PLUGIN_NAME, static_filename)) }}"></script>
      %end
    %end
    %if defined('PLUGIN_DYNAMIC_SCRIPTS') and PLUGIN_DYNAMIC_SCRIPTS:
      %for filename in PLUGIN_DYNAMIC_SCRIPTS:
        <script src="{{ url("render_js", filename=PLUGIN_NAME + "/" + filename) }}?md5={{ js_md5(PLUGIN_NAME + "/" + filename) }}"></script>
      %end
    %end
</head>
<body>
    {{! base }}
</body>
</html>
