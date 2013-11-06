%rebase _layout **locals()
<h1>Foris</h1>

<a href="/logout">odhlásit</a>

<ul>
    %for handler in handlers:
        <a href="/config/{{ handler }}/">{{ handler }}</a>
    %end
</ul>