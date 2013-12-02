%rebase config/base **locals()

<form id="main-form" class="config-form config-form-wifi" action="{{ request.fullpath }}" method="post" autocomplete="off" {{! form.render_html_data() }}>
    <p class="config-description">{{! description }}</p>
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
    <div class="form-buttons">
        <a href="{{ request.fullpath }}" type="submit" class="button grayed">{{ _("Discard changes") }}</a>
        <button type="submit" name="send" class="button">{{ _("Save changes") }}</button>
    </div>
</form>