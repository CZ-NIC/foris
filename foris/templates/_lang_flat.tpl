{{ trans("Language") }}:
<span>{{ iso2to3.get(lang(), lang()) }}</span>
%for code in translations:
  %if code != lang():
    | <a href="{{ url("change_lang", lang=code, backlink=request.fullpath) }}">{{ iso2to3.get(code, code) }}</a>
  %end
%end
