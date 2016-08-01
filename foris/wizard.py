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
from ncclient.operations import RPCError, TimeoutExpiredError

from foris import DEVICE_CUSTOMIZATION
from .core import gettext_dummy as gettext, make_notification_title, ugettext as _
import logging
from .config_handlers import BaseConfigHandler, PasswordHandler, RegionHandler, \
    WanHandler, TimeHandler, LanHandler, UpdaterEulaHandler, WifiHandler
from .nuci import client, filters
from .nuci.configurator import add_config_update, commit
from .nuci.modules.uci_raw import Option, Section, Config, Uci, build_option_uci_tree
from .utils import login_required, messages, require_customization
from .utils.bottle_csrf import CSRFPlugin
from .utils.routing import reverse


logger = logging.getLogger("wizard")


NUM_WIZARD_STEPS = 10


class WizardStepMixin(object):
    template = "wizard/form"
    name = None
    next_step_allowed = None
    next_step_allowed_key = "allowed_step_max"
    is_final_step = False
    # wizard step name
    can_skip_wizard = True

    def call_action(self, action):
        """Call config page action.

        :param action:
        :return: object that can be passed as HTTP response to Bottle
        """
        raise bottle.HTTPError(404, "No actions specified for this page.")

    def call_ajax_action(self, action):
        """Call AJAX action.

        :param action:
        :return: dict of picklable AJAX results
        """
        raise bottle.HTTPError(404, "No AJAX actions specified for this page.")

    def allow_next_step(self, next_step_number=None):
        # this function can be used as a callback for a form
        next_step_number = next_step_number or self.next_step_allowed
        if next_step_number is not None:
            session = request.environ['beaker.session']
            # key in session on the following line should be always
            # set except in the case of the very first start
            session_max_step = int(session.get(WizardStepMixin.next_step_allowed_key, 0))

            if next_step_number > session_max_step:
                allow_next_step_session(next_step_number)
                uci = get_allow_next_step_uci(next_step_number)

                return "edit_config", uci
            else:
                return "none", None

    def mark_wizard_finished(self):
        """Mark wizard as finished.

        :return: tuple for Fapi Form callback
        """
        mark_wizard_finished_session()

        return "edit_config", get_wizard_finished_uci()

    def nuci_write_next_step(self):
        nuci_write = self.allow_next_step()
        if nuci_write[0] == "edit_config" and len(nuci_write) == 2:
            add_config_update(nuci_write[1])
            if self.is_final_step:
                add_config_update(self.mark_wizard_finished()[1])
            commit()

    def default_template(self, **kwargs):
        if kwargs.get("stepnumber"):
            kwargs['title'] = _("Configuration wizard - step %s") % kwargs['stepnumber']
        next_step_url = reverse("wizard_step", number=self.next_step_allowed)
        return template(self.template, can_skip_wizard=self.can_skip_wizard,
                        stepname=self.name, next_step_url=next_step_url, **kwargs)

    def render(self, **kwargs):
        try:
            form = getattr(self, "form")
            # since wizard form is a single-section form...
            first_section = form.sections[0]
            kwargs['first_title'] = first_section.title
            kwargs['first_description'] = first_section.description
        except (NotImplementedError, AttributeError):
            form = None
            kwargs['first_title'] = self.userfriendly_title
            kwargs['first_description'] = None

        return self.default_template(form=form, **kwargs)

    def save(self):
        sup = super(WizardStepMixin, self)
        if hasattr(sup, 'save'):
            def update_allowed_step_max_cb(data):
                return self.allow_next_step()

            def mark_wizard_finished_cb(data):
                return self.mark_wizard_finished()

            extra_callbacks = [update_allowed_step_max_cb]

            if self.is_final_step:
                extra_callbacks.append(mark_wizard_finished_cb)

            return sup.save(extra_callbacks=extra_callbacks)


class WizardStep1(WizardStepMixin, PasswordHandler):
    """
    Setting the password
    """
    name = "password"
    next_step_allowed = 2
    can_skip_wizard = False

    def __init__(self, *args, **kwargs):
        allowed_step_max, wizard_finished = get_wizard_progress()
        require_old = wizard_finished or allowed_step_max >= self.next_step_allowed
        super(WizardStep1, self).__init__(change=require_old, *args, **kwargs)


class WizardStep2(WizardStepMixin, WanHandler):
    """
    WAN settings.
    """
    name = "wan"
    next_step_allowed = 3

    def render(self, **kwargs):
        stats = client.get(filter=filters.stats).find_child("stats")
        wan_if = stats.data['interfaces'].get(self.wan_ifname)
        if not (wan_if and wan_if.get('is_up')):
            messages.warning(_("WAN port has no link, your internet connection probably won't work."))
        return super(WizardStep2, self).render(**kwargs)


class WizardStep3(WizardStepMixin, BaseConfigHandler):
    """
    Network check.
    """
    template = "wizard/connectivity.tpl"
    name = "connectivity"
    next_step_allowed = 4
    userfriendly_title = gettext("Connectivity test")

    def _disable_forwarding(self):
        uci = Uci()
        unbound = Config("unbound")
        uci.add(unbound)
        server = Section("server", "unbound")
        unbound.add(server)
        server.add(Option("forward_upstream", "0"))
        try:
            client.edit_config(uci.get_xml())
            return True
        except (RPCError, TimeoutExpiredError):
            return False

    @staticmethod
    def _check_connection():
        check_results = client.check_connection().check_results
        if check_results:
            has_connection = (check_results.get('IPv4-connectivity')
                              or check_results.get('IPv6-connectivity'))
            resolves = check_results.get('DNS') and check_results.get('DNSSEC')
            if has_connection and resolves:
                return "ok"
            if has_connection:
                return "no_dns"
            return "no_connection"
        return "error"

    def _action_check_connection_noforward(self):
        self._disable_forwarding()
        return self._check_connection()

    def _action_check_connection(self):
        self.nuci_write_next_step()
        return self._check_connection()

    def call_ajax_action(self, action):
        if action == "check_connection":
            check_result = self._action_check_connection()
            return dict(success=True, result=check_result)
        elif action == "check_connection_noforward":
            check_result = self._action_check_connection_noforward()
            return dict(success=True, result=check_result)

        raise ValueError("Unknown Wizard action.")


class WizardStep4(WizardStepMixin, RegionHandler):
    """
    Setting of the region (timezone)
    """
    name = "region"
    next_step_allowed = 5


class WizardStep5(WizardStepMixin, TimeHandler):
    """
    Time settings.
    """
    template = "wizard/time.tpl"
    name = "time"
    next_step_allowed = 6

    def _action_ntp_update(self):
        success = client.ntp_update()
        if success:
            self.nuci_write_next_step()  # allow the next step and save it to uci
        return success

    def call_ajax_action(self, action):
        if action == "ntp_update":
            ntp_ok = self._action_ntp_update()
            return dict(success=ntp_ok)
        elif action == "time_form":
            return dict(success=True, form=self.render(is_xhr=True))
        raise ValueError("Unknown Wizard action.")

    def render(self, **kwargs):
        if kwargs.get("is_xhr"):
            return super(WizardStep5, self).render(**kwargs)

        return self.default_template(form=None, **kwargs)


class WizardStep6(WizardStepMixin, UpdaterEulaHandler):
    """
    Updater.
    """
    template = "wizard/updater.tpl"
    name = "updater"
    next_step_allowed = 7
    userfriendly_title = gettext("System update")

    @require_customization("omnia")
    def _action_submit_eula(self):
        # Save form from handler
        self.form.save()
        agreed = self.form.callback_results['agreed']

        if self.form.callback_results['agreed']:
            next_step = self.next_step_allowed
        else:
            next_step = self.next_step_allowed + 1
        # Allow the next step (if it should be enabled)
        nuci_write = self.allow_next_step(next_step_number=next_step)
        if nuci_write[0] == "edit_config" and len(nuci_write) == 2:
            add_config_update(nuci_write[1])
            commit()
        # Finally, run the updater
        if agreed:
            return dict(success=client.check_updates())
        # Skip to next step if the updater is disabled
        return dict(success=True, redirect=reverse("wizard_step", number=next_step))

    def _action_run_updater(self):
        # this is called by XHR, so we are definitely unable to
        # get past this step with disabled JS
        self.nuci_write_next_step()  # allow the next step and save it to uci
        return client.check_updates()

    def _action_updater_status(self):
        return client.get_updater_status()

    def call_ajax_action(self, action):
        if action == "run_updater":
            run_success = self._action_run_updater()
            return dict(success=run_success)
        elif action == "updater_status":
            status, message, last_activity = self._action_updater_status()
            if status == "offline_pending":
                # it's possible that frontend does not know about this status yet,
                # pretend we are done and handle in the next step
                status = "done"
            result = dict(success=True, status=status, last_activity=last_activity)
            if message:
                result['message'] = message
            return result
        elif action == "submit_eula":
            return self._action_submit_eula()

        raise ValueError("Unknown Wizard action.")


class WizardStep7(WizardStep6):
    """
    Updater - handling offline updates.
    """
    next_step_allowed = 8

    def call_ajax_action(self, action):
        if action == "updater_status":
            status, message, last_activity = self._action_updater_status()
            if status == "done":
                self.nuci_write_next_step()
            result = dict(success=True, status=status, last_activity=last_activity)
            if message:
                result['message'] = message
            return result

        raise ValueError("Unknown Wizard action.")

    def render(self, **kwargs):
        self.nuci_write_next_step()
        status = client.get_updater_status()
        if status[0] == "offline_pending":
            client.reboot()
        elif status[0] == "done":
            bottle.redirect(reverse("wizard_step", number=self.next_step_allowed))
        return super(WizardStep7, self).render(**kwargs)


class WizardStep8(WizardStepMixin, LanHandler):
    """
    LAN settings.
    """
    name = "lan"
    next_step_allowed = 9


class WizardStep9(WizardStepMixin, WifiHandler):
    """
    WiFi settings.
    """
    template = "wizard/wifi"
    name = "wifi"
    next_step_allowed = 10
    is_final_step = True

    def get_form(self):
        form = super(WizardStep9, self).get_form()

        if not form:
            # enable next step if no WiFi cards were detected
            self.nuci_write_next_step()

        return form


class WizardStep10(WizardStepMixin, BaseConfigHandler):
    """
    Show the activation code.
    """
    can_skip_wizard = False
    template = "wizard/registration.tpl"

    def render(self, **kwargs):
        kwargs['notifications'] = client.get_messages().restarts
        kwargs['make_notification_title'] = make_notification_title
        if DEVICE_CUSTOMIZATION == "omnia":
            foris_conf = client.get(filter=filters.create_config_filter("foris"))
            agreed_opt = foris_conf.find_child("uci.foris.eula.agreed_updater")
            agreed_updater = agreed_opt and bool(int(agreed_opt.value))
            return template("wizard/finished.tpl",
                            title=_("Installation finished"),
                            stepname=self.name,
                            can_skip_wizard=self.can_skip_wizard,
                            agreed_updater=agreed_updater, **kwargs)

        registration = client.get_registration()
        # show only restart notifications
        if registration:
            return self.default_template(code=registration.value, **kwargs)
        else:
            return template('wizard/registration-failure.tpl', stepname=self.name,
                            can_skip_wizard=self.can_skip_wizard, **kwargs)


def get_wizard(number):
    """WizardStep class factory.

    :param number:
    :return:
    """
    class_name = "WizardStep%s" % number
    try:
        wiz = globals()[class_name]
        if not issubclass(wiz, WizardStepMixin):
            raise AttributeError
    except (KeyError, AttributeError):
        raise bottle.HTTPError(404, "Wizard step '%s' not found" % number)
    check_step_allowed_or_redirect(number)
    return wiz


def get_wizard_progress():
    """Get number of the allowed step and information whether wizard was finished
    from session, or from Foris Uci config if session is empty.

    Updates session variables of max allowed step and wizard finished flag if value was
    retrieved from Uci config.

    :return: step number of last allowed step (default is 1) and boolean flag - wizard is finished
    :rtype: tuple(int, bool)
    """
    session = request.environ['beaker.session']
    allowed_sess = session.get(WizardStepMixin.next_step_allowed_key, None)
    is_finished = session.get("wizard_finished", False)
    try:
        if not allowed_sess:
            data = client.get(filter=filters.foris_config)
            next_step_option = data.find_child("uci.foris.wizard.%s"
                                               % WizardStepMixin.next_step_allowed_key)
            is_finished_option = data.find_child("uci.foris.wizard.finished")
            next_step_allowed = int(next_step_option.value) if next_step_option else 1
            is_finished = bool(int(is_finished_option.value)) if is_finished_option else False
            # write to session so we don't have to check config later
            allow_next_step_session(next_step_allowed)
            if is_finished:
                mark_wizard_finished_session()
            return next_step_allowed, is_finished
        return int(allowed_sess), is_finished
    except ValueError:
        return 1, False


def check_step_allowed_or_redirect(step_number):
    step_number = int(step_number)
    allowed_step_max, wizard_finished = get_wizard_progress()
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
    return build_option_uci_tree("foris.wizard.%s" % WizardStepMixin.next_step_allowed_key,
                                 "config", step_number)


def get_wizard_finished_uci():
    """
    Gets Uci element for marking wizard finished.

    :return: Uci element for marking wizard finished
    """
    return build_option_uci_tree("foris.wizard.finished", "config", True)


def mark_wizard_finished_session():
    """Mark wizard as finished in session.

    :return: None
    """
    session = request.environ['beaker.session']
    session["wizard_finished"] = True
    session.save()


@login_required
def ajax(number=1):
    check_step_allowed_or_redirect(number)
    action = request.GET.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    Wizard = get_wizard(number)
    wiz = Wizard(request.POST)
    try:
        result = wiz.call_ajax_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown Wizard action.")


@login_required
def wizard():
    return bottle.template("wizard/index")


@login_required
def step(number=1):
    Wizard = get_wizard(number)
    wiz = Wizard()
    return wiz.render(stepnumber=number)


@login_required
def step_post(number=1):
    Wizard = get_wizard(number)
    wiz = Wizard(request.POST)
    if request.is_xhr:
        # only update is allowed via XHR
        return wiz.render(is_xhr=True)

    try:
        if wiz.save():
            bottle.redirect(reverse("wizard_step", number=int(number) + 1))
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        messages.error(_("Configuration could not be saved due to an internal error."))
        logger.exception("Error when saving form.")
    messages.warning(_("There were some errors in your input."))
    logger.warning("Form not saved.")
    return wiz.render(stepnumber=number)


@login_required
def skip():
    allowed_step_max, wizard_finished = get_wizard_progress()
    last_step_number = min(NUM_WIZARD_STEPS, allowed_step_max)
    Wizard = get_wizard(last_step_number)
    if Wizard.can_skip_wizard or allowed_step_max >= NUM_WIZARD_STEPS or wizard_finished:
        # mark wizard as finished
        mark_wizard_finished_session()
        add_config_update(get_wizard_finished_uci())
        # update last step number
        allow_next_step_session(NUM_WIZARD_STEPS)
        add_config_update(get_allow_next_step_uci(NUM_WIZARD_STEPS))
        commit()
        bottle.redirect(reverse("config_index"))

    raise bottle.HTTPError(403, "Action not allowed.")


def init_app():
    app = Bottle()
    app.install(CSRFPlugin())
    app.route("/step/<number:re:\d+>/ajax", method=['GET', 'POST'], name="wizard_ajax", callback=ajax)
    app.route("/", name="wizard_index", callback=wizard)
    app.route("/step/<number:re:\d+>", name="wizard_step", callback=step)
    app.route("/step/<number:re:\d+>", method="POST", callback=step_post)
    app.route("/skip", name="wizard_skip", callback=skip)
    return app
