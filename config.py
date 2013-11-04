from bottle import Bottle, request, template
import bottle
import logging
from utils import login_required
import wizard


logger = logging.getLogger("admin")


app = Bottle()


handler_map = {
    'password': wizard.WizardStep1,
    'wan': wizard.WizardStep2,
    'lan': wizard.WizardStep5,
    'wifi': wizard.WizardStep6,
}


def get_handler(handler_name):
    Handler = handler_map.get(handler_name)
    if Handler is None:
        raise bottle.HTTPError(404, "Unknown configuration page.")
    return Handler


def render_form(form, **kwargs):
    # same premise as in wizard form - we are handling single-section ForisForm
    first_section = form.sections[0]
    title = first_section.title
    description = first_section.description
    return template("config/main", form=form, title=title, description=description, **kwargs)


@app.route("/<handler_name:re:.+>/")
@login_required
def config_get(handler_name):
    Handler = get_handler(handler_name)
    handler = Handler()
    form = handler.form
    return render_form(form)


@app.route("/<handler_name:re:.+>/", method="POST")
@login_required
def config_post(handler_name):
    Handler = get_handler(handler_name)
    handler = Handler(request.POST)
    if request.is_xhr:
        # only update is allowed
        logger.debug("ajax request")
        request.POST.pop("update", None)
        return dict(html=render_form(handler.form, is_xhr=True))

    try:
        if handler.save():
            logger.info("saved")
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        pass
    return render_form(handler.form)


@app.route("/<handler_name:re:.+>/ajax")
@login_required
def config_ajax(handler_name):
    action = request.GET.get("action")
    if not action:
        raise bottle.HTTPError(404, "AJAX action not specified.")
    Handler = get_handler(handler_name)
    handler = Handler()
    try:
        result = handler.call_action(action)
        return result
    except ValueError:
        raise bottle.HTTPError(404, "Unknown action.")