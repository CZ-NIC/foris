%for section in form.sections:
    %if section.active_fields:
        <br />
        <h4>{{ section.title }}</h4>
        %if section.description:
            <p class="config-section-description">{{ section.description }}</p>
        %end
        %for field in section.active_fields:
            %include("_field.tpl", field=field)
            %if field.name == "radio0-hwmode" and DEVICE_CUSTOMIZATION == "omnia" and field.field.value == "11g":
        <div class="row">
            <p class="form-note">
                {{ trans("If you want to use this card for 2.4GHz bands, correction of cables connected to diplexers is needed! Factory default setting: Cables from big card connected to 5GHz, cables from small card connected to 2.4GHz diplexer part.") }}
            <p>
        </div>
        %end
    %end
%end
