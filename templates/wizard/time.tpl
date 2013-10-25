%if not defined('is_xhr'):
    %rebase _layout **locals()
%end

%if form:
    <form action="" method="post">
        {{! form.render() }}
        <input type="submit" name="send" value="Send">
    </form>
%else:
    <div id="wizard-time">
        Probíhá synchronizace času na routeru s časem v internetu. Chvilku strpení...
        >>TODO: obrázek-loader<<
    </div>

    <script>
        $(document).ready(function(){
            ForisWizard.ntpUpdate();
        });
    </script>
%end