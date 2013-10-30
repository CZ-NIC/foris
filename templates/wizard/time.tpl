%rebase wizard/base **locals()

%if form:
    <form class="wizard-form" action="" method="post">
        <h1>{{ first_title }}</h1>
        <p>{{ first_description }}</p>
        %for field in form.active_fields:
            <div>{{! field.label_tag }}{{! field.render() }}</div>
        %end
        <button class="button-next" type="submit" name="send" class="button-arrow-right">Next</button>
    </form>
%else:
    <div id="wizard-time">
        <h1>Nastavení času</h1>
        <div id="time-progress" class="background-progress">
            <img src="/static/img/loader.gif" alt="Probíhá načítání..."><br>
            Probíhá synchronizace času na routeru s časem v internetu.<br>
            Chvilku strpení...
        </div>

        <div id="time-success">
            <img src="/static/img/success.png" alt="Hotovo"><br>
            <p>Čas byl úspěšně synchronizován, můžete postoupit k dalšímu kroku.</p>
            <a class="button-next" href="/wizard/step/4">Next</a>
        </div>
    </div>

    <script>
        $(document).ready(function(){
            ForisWizard.ntpUpdate();
        });
    </script>
%end