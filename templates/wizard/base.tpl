%if not defined('is_xhr'):
    %rebase _layout **locals()
%end

<form id="wizard-form" action="" method="post">
    {{! form.render() }}
    <input type="submit" name="send" value="Send">
</form>