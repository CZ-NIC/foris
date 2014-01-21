%for message in get_messages():
  <div class="message {{ message.classes }}">
    {{! message.text }}
  </div>
%end