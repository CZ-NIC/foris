%rebase _layout **locals()
<h1>Foris</h1>
<h2>roscesňýk</h2>

%if user_authenticated():
    <a href="{{ url("logout") }}">odhlásit</a>
%else:
    <form action="{{ request.fullpath }}" method="POST">
        <label for="field-password">{{ _("Password") }}</label>
        <input id="field-password" type="password" name="password">
        <button class="button" type="submit">{{ _("Log in") }}</button>
    </form>
%end

<ul>
    <li><a href="{{ url("uci_index") }}">about:config</a></li>
    <li><a href="{{ url("wizard_index") }}">kuzelňik</a></li>
    <li><a href="{{ url("config_index") }}">dlaší natavení</a></li>
</ul>