from bottle import Bottle, template, request
import bottle
import logging
from config_handlers import BaseConfigHandler, PasswordHandler, WanHandler, TimeHandler,\
    LanHandler, WifiHandler
from nuci import client
from utils import login_required


logger = logging.getLogger("wizard")


class WizardStepMixin(object):
    template = "wizard/form"
    name = None
    # wizard step name

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


class WizardStep1(PasswordHandler, WizardStepMixin):
    """
    Setting the password
    """
    name = "password"


class WizardStep2(WanHandler, WizardStepMixin):
    """
    WAN settings.
    """
    name = "wan"


class WizardStep3(TimeHandler, WizardStepMixin):
    """
    Time settings.
    """
    template = "wizard/time.tpl"
    name = "time"

    def render(self, **kwargs):
        if kwargs.get("is_xhr"):
            return super(WizardStep3, self).render(**kwargs)

        return self.default_template(form=None, **kwargs)


class WizardStep4(BaseConfigHandler, WizardStepMixin):
    """
    Updater.
    """
    template = "wizard/updater.tpl"
    name = "updater"

    def _action_run_updater(self):
        return client.check_updates()

    def _action_updater_status(self):
        return client.get_updater_status()

    def call_action(self, action):
        if action == "run_updater":
            run_success = self._action_run_updater()
            return dict(success=run_success)
        elif action == "updater_status":
            status, message = self._action_updater_status()
            result = dict(success=True, status=status)
            if message:
                result['message'] = message
            return result

        raise ValueError("Unknown Wizard action.")


class WizardStep5(LanHandler, WizardStepMixin):
    """
    LAN settings.
    """
    name = "lan"


class WizardStep6(WifiHandler, WizardStepMixin):
    """
    WiFi settings.
    """
    name = "wifi"


class WizardStep7(BaseConfigHandler, WizardStepMixin):
    """
    Show the activation code.
    """
    template = "wizard/registration.tpl"

    def render(self, **kwargs):
        registration = client.get_registration()
        return self.default_template(code=registration.value, **kwargs)


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
    return wiz


@app.route("/step/<number:re:\d+>/ajax")
@login_required
def ajax(number=1):
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


@app.route("/", name="wizard-step")
@login_required
def wizard():
    bottle.redirect("/wizard/step/1")


@app.route("/step/<number:re:\d+>", name="wizard-step")
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
        # only update is allowed
        logger.debug("ajax request")
        request.POST.pop("update", None)
        return dict(html=wiz.render(is_xhr=True))

    try:
        if wiz.save():
            bottle.redirect("/wizard/step/%s" % str(int(number) + 1))
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        pass
    return wiz.render(stepnumber=number)