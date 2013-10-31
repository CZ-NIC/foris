%rebase _layout **locals()
<h1>Foris</h1>
<h2>roscesňýk</h2>

%if user_authenticated():
    <a href="/logout">odhlásit</a>
%else:
    <form action="" method="POST">
        <label for="field-password">{{ _("Password") }}</label>
        <input id="field-password" type="password" name="password">
        <button class="button" type="submit">{{ _("Log in") }}</button>
    </form>
%end

<ul>
    <li><a href="uci/">about:config</a></li>
    <li><a href="wizard/">kuzelňik</a></li>
</ul>