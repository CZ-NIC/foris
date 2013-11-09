from bottle import Bottle, request, template
import bottle
from config_handlers import *
import logging
from utils import login_required


logger = logging.getLogger("admin")


app = Bottle()


# names of handlers used in their URL
# use dash-separated names, underscores in URL are ugly
handler_map = {
    'password': PasswordHandler,
    'wan': WanHandler,
    'lan': LanHandler,
    'wifi': WifiHandler,
    'system-password': SystemPasswordHandler,
}


def get_handler(handler_name):
    Handler = handler_map.get(handler_name)
    if Handler is None:
        raise bottle.HTTPError(404, "Unknown configuration page.")
    return Handler


def render(form, **kwargs):
    # same premise as in wizard form - we are handling single-section ForisForm
    first_section = form.sections[0]
    title = first_section.title
    description = first_section.description
    return template("config/main", form=form, title=title, description=description,
                    handlers=handler_map.keys(), **kwargs)


@app.route("/", name="config_index")
@login_required
def index():
    return template("config/index", handlers=handler_map.keys())


@app.route("/<handler_name:re:.+>/", name="config_handler")
@login_required
def handler_get(handler_name):
    Handler = get_handler(handler_name)
    handler = Handler()
    return render(handler.form, active_handler_key=handler_name)


@app.route("/<handler_name:re:.+>/", method="POST")
@login_required
def handler_post(handler_name):
    Handler = get_handler(handler_name)
    handler = Handler(request.POST)
    if request.is_xhr:
        # only update is allowed
        logger.debug("ajax request")
        request.POST.pop("update", None)
        return dict(html=render(handler.form, is_xhr=True))

    try:
        if handler.save():
            bottle.redirect(request.fullpath)
    except TypeError:
        # raised by Validator - could happen when the form is posted with wrong fields
        pass
    return render(handler.form, active_handler_key=handler_name)


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