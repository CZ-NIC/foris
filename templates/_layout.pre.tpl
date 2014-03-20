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
<html>
<head>
    <meta charset="utf-8">
    <title>{{ trans("Turris router administration interface") }}</title>
    <link href="{{ static("css/screen.css") }}?md5=MD5SUM" rel="stylesheet" media="screen">
    <!--[if lt IE 9]>
        <script src="{{ static("js/contrib/html5.js") }}"></script>
    <![endif]-->
    <script src="{{ static("js/contrib/jquery.min.js") }}"></script>
    <script src="{{ static("js/contrib/parsley.min.js") }}"></script>
    <script src="{{ static("js/parsley.foris-extend.min.js") }}?md5=MD5SUM"></script>
    <script src="{{ static("js/foris.min.js") }}?md5=MD5SUM"></script>
%if lang() == 'cs':
    <script src="{{ static("js/parsley.messages.cs.min.js") }}?md5=MD5SUM"></script>
    <script src="{{ static("js/foris.cs.min.js") }}?md5=MD5SUM"></script>
%end
</head>
<body>
    <div id="language-switch">
      {{ trans("Language") }}:
      <a href="{{ url("change_lang", lang="cs", backlink=request.fullpath) }}">CZE</a>
      | <a href="{{ url("change_lang", lang="en", backlink=request.fullpath) }}">ENG</a>
    </div>
    <div id="page">
        %include
    </div>
</body>
</html>
