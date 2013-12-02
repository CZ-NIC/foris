%if not defined('is_xhr'):
    %rebase _layout **locals()
    <div id="config-header">
        <h1>{{ _("Settings") }}</h1>
        <div class="logo-turris"><img src="{{ static("img/logo-turris.png") }}"></div>
        <a id="logout" href="{{ url("logout") }}">{{ _("Log out") }}</a>
    </div>


    <div id="config-content">

    <ul class="tabs">
        %for config_page in config_pages:
            <li \\
%if defined("active_config_page_key") and config_page['slug'] == active_config_page_key:
class="active" \\
%end\\
><a href="{{ url("config_page", page_name=config_page['slug']) }}">{{ _(config_page['name']) }}</a></li>
        %end
    </ul>
%end

    %include

%if not defined('is_xhr'):
    </div>
%end