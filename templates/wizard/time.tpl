%rebase wizard/base **locals()

%if form:
    <form action="" method="post">
        {{! form.render() }}
        <input type="submit" name="send" value="Send">
    </form>
%else:
    <div id="wizard-time">
        <h1>Nastavení času</h1>
        Probíhá synchronizace času na routeru s časem v internetu. Chvilku strpení...<br>
        <img src="/static/img/loader.gif" alt="Probíhá načítání...">
    </div>

    <script>
        $(document).ready(function(){
            ForisWizard.ntpUpdate();
        });
    </script>
%end