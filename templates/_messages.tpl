%for message in get_messages():
  <div class="message {{ message.classes }}">
    {{! message.text }}
  </div>
%end

<noscript>
  <div class="message info">
    {{ trans("This page requires JavaScript for proper function. Please enable it and refresh the page.") }}
  </div>
</noscript>