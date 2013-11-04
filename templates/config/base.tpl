%if not defined('is_xhr'):
    %rebase _layout **locals()

    <div id="admin-content">
%end

    %include

%if not defined('is_xhr'):
    </div>
%end