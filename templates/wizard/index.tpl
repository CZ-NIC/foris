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
%rebase _layout **locals()

%include wizard/_header can_skip_wizard=False, stepnumber=0

<h1>Vítejte v nastavení routeru Turris</h1>

<p>Než začnete router používat, je třeba provést jeho prvotní nastavení. K tomu slouží tento jednoduchý průvodce základní konfigurací. Po jeho dokončení bude router připraven k běžnému použití.</p>
<hr>
<p>Pokud chcete obnovit dříve uložené nastavení routeru nebo z jiného důvodu přeskočit tohoto průvodce, můžete tak učinit po nastavení uživatelského hesla v prvním kroku průvodce.</p>

<a href="{{ url("wizard_step", number=1) }}" class="button-next" type="submit" name="send" class="button-arrow-right">{{ trans("Begin installation") }}</a>