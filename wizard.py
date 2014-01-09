# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2013 CZ.NIC, z.s.p.o. <http://www.nic.cz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from bottle import Bottle, template, request
import bottle
import logging
from config_handlers import BaseConfigHandler, PasswordHandler, WanHandler, TimeHandler,\
    LanHandler, WifiHandler
from nuci import client, filters
from nuci.configurator import add_config_update, commit
from nuci.modules.uci_raw import Option, Section, Config, Uci
from utils import login_required
from utils.bottle_csrf import CSRFPlugin
from utils.routing import reverse


logger = logging.getLogger("wizard")


app = Bottle()
app.install(CSRFPlugin())


NUM_WIZARD_STEPS = 7


class WizardStepMixin(object):
    template = "wizard/form"
    name = None
    next_step_allowed = None
    next_step_allowed_key = "allowed_step_max"
    # wizard step name
    can_skip_wizard = True

    def allow_next_step(self):
        # this function can be used as a callback for a form
        if self.next_step_allowed is not None:
            session = request.environ['beaker.session']
            # key in session on the following line should be always
            # set except in the case of the very first start
            session_max_step = int(session.get(WizardStepMixin.next_step_allowed_key, 0))
            
            if self.next_step_allowed > session_max_step:
                allow_next_step_session(self.next_step_allowed)
                uci = get_allow_next_step_uci(self.next_step_allowed)

                return "edit_config", uci
            else:
                return "none", None
    
    def nuci_write_next_step(self):
        nuci_write = self.allow_next_step()
        if nuci_write[0] == "edit_config" and len(nuci_write) == 2:
            add_config_update(nuci_write[1])
            commit()

    def default_template(self, **kwargs):
        return template(self.template, can_skip_wizard=self.can_skip_wizard,
                        stepname=self.name, **kwargs)

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
            # self.allow_next_step()
            
            def update_allowed_step_max_cb(data):
                return self.allow_next_step()
            
            return sup.save(extra_callbacks=[update_allowed_step_max_cb])


class WizardStep1(WizardStepMixin, PasswordHandler):
    """
    Setting the password
    """
    name = "password"
    next_step_allowed = 2
    can_skip_wizard = False


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
            self.nuci_write_next_step() # allow the next step and save it to uci
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
        self.nuci_write_next_step() # allow the next step and save it to uci
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
    template = "wizard/wifi"
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
            return self.default_template(code=registration.value, **kwargs)
        else:
            return template('wizard/registration-failure.tpl', stepname=self.name,
                            can_skip_wizard=self.can_skip_wizard, **kwargs)


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
    bottle.redirect(reverse("wizard_step", number=allowed_step_max))


def allow_next_step_session(step_number):
    """
    Allow step in session.

    :param step_number: step to allow
    """
    session = request.environ['beaker.session']
    # update session variable
    session[WizardStepMixin.next_step_allowed_key] = step_number
    session.save()


def get_allow_next_step_uci(step_number):
    """
    Gets Uci element for allowing step with specified number.


    :param step_number: step to allow
    :return: Uci element for allowing specified step
    """
    uci = Uci()
    foris = Config("foris")
    uci.add(foris)
    wizard = Section("wizard", "config")
    foris.add(wizard)
    wizard.add(Option(WizardStepMixin.next_step_allowed_key, step_number))

    return uci


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


@app.route("/skip", name="wizard_skip")
def skip():
    allowed_step_max = int(get_allowed_step_max())
    last_step_number = min(NUM_WIZARD_STEPS, allowed_step_max)
    Wizard = get_wizard(last_step_number)
    if Wizard.can_skip_wizard:
        allow_next_step_session(NUM_WIZARD_STEPS)
        uci = get_allow_next_step_uci(NUM_WIZARD_STEPS)
        client.edit_config(uci.get_xml())
        bottle.redirect(reverse("config_index"))

    raise bottle.HTTPError(403, "Action not allowed.")
