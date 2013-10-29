%if not defined('is_xhr'):
    %rebase _layout **locals()

    <div id="wizard-header">
        <img src="/static/img/logo-turris.png" alt="Project:Turris">
        <span class="stepno"><span class="stepno-current">{{ stepnumber }}</span> / 7</span>
    </div>

%if stepname:
    <div id="wizard-icon"><img src="/static/img/wizard/step-{{ stepname }}.png"></div>
%end
    <div id="wizard-content">
%end

    %include

%if not defined('is_xhr'):
    </div>
%end