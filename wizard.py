from bottle import Bottle, template, request
import bottle
import logging
from config_handlers import BaseConfigHandler, PasswordHandler, WanHandler, TimeHandler,\
    LanHandler, WifiHandler
from nuci import client, filters
from nuci.modules.uci_raw import Option, Section, Config, Uci
from utils import login_required
from utils.routing import reverse
from foris import gettext as _

logger = logging.getLogger("wizard")


class WizardStepMixin(object):
    template = "wizard/form"
    name = None
    next_step_allowed = None
    next_step_allowed_key = "allowed_step_max"
    # wizard step name

    def allow_next_step(self):
        if self.next_step_allowed is not None:
            session = request.environ['beaker.session']
            session[WizardStepMixin.next_step_allowed_key] = self.next_step_allowed
            session.save()

    def default_template(self, **kwargs):
        return template(self.template, stepname=self.name, **kwargs)

    def render(self, **kwargs):
        try:
            form = getattr(self, "form")
            # since wizard form is a single-section form...
            first_section = form.sections[0]
            kwargs['first_title'] = first_section.title
            kwargs['first_description'] = first_section.description
        except (NotImplementedError, AttributeError):
            form = None
            kwargs['first_title'] = None
            kwargs['first_description'] = None

        return self.default_template(form=form, **kwargs)

    def save(self):
        sup = super(WizardStepMixin, self)
        if hasattr(sup, 'save'):
            self.allow_next_step()

            def update_allowed_step_max_cb(data):
                uci = Uci()
                foris = Config("foris")
                uci.add(foris)
                wizard = Section("wizard", "config")
                foris.add(wizard)
                wizard.add(Option(WizardStepMixin.next_step_allowed_key, self.next_step_allowed))

                return "edit_config", uci

            return sup.save(extra_callbacks=[update_allowed_step_max_cb])


class WizardStep1(WizardStepMixin, PasswordHandler):
    """
    Setting the password
    """
    name = "password"
    next_step_allowed = 2


class WizardStep2(WizardStepMixin, WanHandler):
    """
    WAN settings.
    """
    name = "wan"
    next_step_allowed = 3


class WizardStep3(WizardStepMixin, TimeHandler):
    """
    Time settings.
    """
    template = "wizard/time.tpl"
    name = "time"
    next_step_allowed = 4

    def _action_ntp_update(self):
        success = TimeHandler._action_ntp_update(self)
        if success:
            self.allow_next_step()
        return success

    def render(self, **kwargs):
        if kwargs.get("is_xhr"):
            return super(WizardStep3, self).render(**kwargs)

        return self.default_template(form=None, **kwargs)


class WizardStep4(WizardStepMixin, BaseConfigHandler):
    """
    Updater.
    """
    template = "wizard/updater.tpl"
    name = "updater"
    next_step_allowed = 5

    def _action_run_updater(self):
        # this is called by XHR, so we are definitely unable to
        # get past this step with disabled JS
        self.allow_next_step()
        return client.check_updates()

    def _action_updater_status(self):
        return client.get_updater_status()

    def call_action(self, action):
        if action == "run_updater":
            run_success = self._action_run_updater()
            return dict(success=run_success)
        elif action == "updater_status":
            status, message, last_activity = self._action_updater_status()
            result = dict(success=True, status=status, last_activity=last_activity)
            if message:
                result['message'] = message
            return result

        raise ValueError("Unknown Wizard action.")


class WizardStep5(WizardStepMixin, LanHandler):
    """
    LAN settings.
    """
    name = "lan"
    next_step_allowed = 6


class WizardStep6(WizardStepMixin, WifiHandler):
    """
    WiFi settings.
    """
    name = "wifi"
    next_step_allowed = 7


class WizardStep7(WizardStepMixin, BaseConfigHandler):
    """
    Show the activation code.
    """
    template = "wizard/registration.tpl"

    def render(self, **kwargs):
        registration = client.get_registration()
        if registration:
            msgtext = _("To finish the process of the router installation, fill "
                        "in the following code <strong>%s</strong> on the EUKI "
                        "website. TODO: add more explanation, link to EUKI,...")
            msgtext = msgtext % registration.value
            return self.default_template(msgtext=msgtext, **kwargs)
        else:
            return template('wizard/registration-failure.tpl', stepname=self.name, **kwargs)


app = Bottle()


def get_wizard(number):
    """WizardStep class factory.

    :param number:
    :return:
    """
    class_name = "WizardStep%s" % number
    wiz = globals()[class_name]
    if not issubclass(wiz, WizardStepMixin):
        raise bottle.HTTPError(404, "Wizard step not found: %s" % number)
    check_step_allowed_or_redirect(number)
    return wiz


def get_allowed_step_max():
    session = request.environ['beaker.session']
    allowed_sess = session.get(WizardStepMixin.next_step_allowed_key, None)
    if not allowed_sess:
        data = client.get(filter=filters.foris_config)
        next_step_option = data.find_child("uci.foris.wizard.%s" % WizardStepMixin.next_step_allowed_key)
        if next_step_option:
            return next_step_option.value
        return next_step_option
    return allowed_sess


def check_step_allowed_or_redirect(step_number):
    step_number = int(step_number)
    session = request.environ['beaker.session']
    allowed_step_max = int(session.get(WizardStepMixin.next_step_allowed_key, 1))
    if step_number <= allowed_step_max:
        return True
    logger.warning("redirecting")
    bottle.redirect(reverse("wizard_step", number=allowed_step_max))


@app.route("/step/<number:re:\d+>/ajax")
@login_required
def ajax(number=1):
    check_step_allowed_or_redirect(number)
    action = request.GET.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    Wizard = get_wizard(number)
    wiz = Wizard()
    try:
        result = wiz.call_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown Wizard action.")


@app.route("/", name="wizard_index")
@login_required
def wizard():
    bottle.redirect(reverse("wizard_step", number=1))


@app.route("/step/<number:re:\d+>", name="wizard_step")
@login_required
def step(number=1):
    Wizard = get_wizard(number)
    wiz = Wizard()
    return wiz.render(stepnumber=number)


@app.route("/step/<number:re:\d+>", method="POST")
@login_required
def step_post(number=1):
    Wizard = get_wizard(number)
    wiz = Wizard(request.POST)
    if request.is_xhr:
        # only update is allowed via XHR
        request.POST.pop("update", None)
        return dict(html=wiz.render(is_xhr=True))

    try:
        if wiz.save():
            bottle.redirect(reverse("wizard_step", number=int(number) + 1))
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        pass
    return wiz.render(stepnumber=number)
