%for section in form.sections:
    %if section.active_fields:
        <br />
        <h4>{{ section.title }}</h4>
        %if section.description:
            <p class="config-section-description">{{ section.description }}</p>
        %end
        %for field in section.active_fields:
            % radio_number = "".join([e for e in field.name if e.isdigit()])
            %include("_field.tpl", field=field)
            %if field.name == "radio0-hwmode" and foris_info.device_customization == "omnia" and field.field.value == "11g":
        <div class="row">
            <p class="form-note">
                {{ trans("If you want to use this card for 2.4GHz bands, correction of cables connected to diplexers is needed! Factory default setting: Cables from big card connected to 5GHz, cables from small card connected to 2.4GHz diplexer part.") }}
            <p>
        </div>
            %end
            %if field.name.endswith("-password"):
        <div class="wifi-qr row" id="wifi-qr-{{ radio_number }}">
            <img src="{{ static("img/QR_icon.svg") }}" alt="{{ trans("QR code") }}" title="{{ trans("Show QR code") }}">
            <div id="wifi-qr-radio{{ radio_number }}" class="wifi-qr-box"></div>
        </div>
            %end
            %if field.name.endswith("guest_password"):
        <div class="wifi-qr row" id="wifi-qr-guest-{{ radio_number }}">
            <img src="{{ static("img/QR_icon.svg") }}" alt="{{ trans("QR code") }}" title="{{ trans("Show QR code") }}">
            <div id="wifi-qr-guest-radio{{ radio_number }}" class="wifi-qr-box"></div>
        </div>
            %end
        %end
    %end
%end
