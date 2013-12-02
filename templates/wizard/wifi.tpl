%rebase wizard/base **locals()

<form id="main-form" class="wizard-form wizard-form-wifi" action="{{ request.fullpath }}" method="post" autocomplete="off" {{! form.render_html_data() }}>
    <h1>{{ first_title }}</h1>
    <p class="wizard-description">{{! first_description }}</p>
    %for field in form.active_fields:
        %if field.hidden:
            {{! field.render() }}
        %else:
        <div>
            {{! field.label_tag }}
            {{! field.render() }}
            %if field.hint:
                <img class="field-hint" src="{{ static("img/icon-help.png") }}" title="{{ field.hint }}">
            %end
        </div>
        %end
    %end
    <div id="wifi-qr">
    </div>
    <script src="{{ static("js/contrib/jquery.qrcode-0.7.0.min.js") }}"></script>
    <script>
        $(document).ready(function() {
            ForisWizard.initWiFiQR();
        });
    </script>
    <button class="button-next button-arrow-right" type="submit" name="send">{{ _("Next") }}</button>
</form>
<div id="form-error-box"></div>
