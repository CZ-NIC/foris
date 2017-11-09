<p>
  {{ trans("One of the most important features of router Turris are automatic system updates. Thanks to this function your router's software stays up to date and offers better protection against attacks from the Internet.") }}
</p>

<p>{{! trans("It is <strong>highly recommended</strong> to have this feature <strong>turned on</strong>. If you decide to disable it, be warned that this might weaken the security of your router and network in case flaws in the software are found.") }}</p>

<p>{{! trans('By turning the automatic updates on, you agree to this feature\'s license agreement. More information is available <a href="#" id="toggle-eula">here</a>.') }}</p>

<div id="eula-text">

  <p>{{ trans("Most important points from the license agreement:") }}</p>

  <ul>
    <li>{{ trans("Automatic updates are offered to the Turris router owners free of charge.") }}</li>
    <li>{{ trans("Updates are prepared exclusively by CZ.NIC, z. s. p. o.") }}</li>
    <li>{{ trans("Enabling of the automatic updates is a prerequisite for additional security features of Turris router.") }}</li>
    <li>{{ trans("Automatic updates take place at the time of their release, the time of installation cannot be influenced by the user.") }}</li>
    <li>{{ trans("Having the automatic updates turned on can result in increased Internet traffic on your router. Expenses related to this increase are covered by you.") }}</li>
    <li>{{ trans("Automatic updates cannot protect you against every attack coming from the Internet. Please do not forget to protect your workstations and other devices by installing antivirus software and explaining to your family members how to stay safe on the Internet.") }}</li>
    <li>{{ trans("CZ.NIC, z. s. p. o. does not guarantee the availability of this service and is not responsible for any damages caused by the automatic updates.") }}</li>
  </ul>

  <p class="eula-summary">
    {{! trans('By enabling of the automatic updates, you confirm that you are the owner of this Turris router and you agree with the full text of the <a href="https://www.turris.cz/omnia-updater-eula">license agreement</a>.') }}
  </p>
</div>

<script>
  $('#toggle-eula').click(function (e) {
    e.preventDefault();
    $('#eula-text').toggle();
  });
</script>
