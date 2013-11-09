%if not defined('is_xhr'):
    %rebase _layout **locals()
    <div id="config-header">
        <h1>{{ _("Settings") }}</h1>
        <div class="logo-turris"><img src="{{ static("img/logo-turris.png") }}"></div>
        <a id="logout" href="{{ url("logout") }}">{{ _("Log out") }}</a>
    </div>


    <div id="config-content">

    <ul class="tabs">
        %for handler in handlers:
            <li \\
%if defined("active_handler_key") and handler == active_handler_key:
class="active" \\
%end\\
><a href="{{ url("config_handler", handler_name=handler) }}">{{ handler }}</a></li>
        %end
    </ul>
%end

    %include

%if not defined('is_xhr'):
    </div>
%end