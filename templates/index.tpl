%rebase _layout **locals()
<div id="login-page">
    <h1><img src="{{ static("img/logo-turris.png") }}" alt="{{ _("Project:Turris") }}"></h1>

    %if user_authenticated():
        <a href="{{ url("logout") }}">{{ _("Log out") }}</a>
    %else:
        <form action="{{ request.fullpath }}" method="POST">
            <label for="field-password">{{ _("Password") }}</label>
            <input id="field-password" type="password" name="password" placeholder="{{ _("Password") }}">
            <button class="button" type="submit">{{ _("Log in") }}</button>
        </form>
    %end
</div>