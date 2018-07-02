import bottle
import os


from foris import fapi, validators
from foris.config import ConfigPageMixin, add_config_page
from foris.config_handlers import BaseConfigHandler
from foris.form import Number
from foris.plugins import ForisPlugin
#from foris.state import current_state
from foris.utils.translators import gettext_dummy as gettext, ugettext as _


# This represents a main form handler
class SamplePluginConfigHandler(BaseConfigHandler):
    # gettext() triggers lazy_translated text
    # it is also used for detecting translations during foris_make_messages cmd

    userfriendly_title = gettext("Sample")
    ###
    slices = 10
    ###

    def get_form(self):
        #data= current_state.backend.perform("sample", "get_slices")
        ###
        data = {"slices": SamplePluginConfigHandler.slices}
        ###

        if self.data:
            # Update from post (used when the form is updated via ajax)
            data.update(self.data)

        form = fapi.ForisForm("sample", data)
        section = form.add_section(
            name="main_section",
            title=self.userfriendly_title,
        )
        # _() translates the string immediatelly
        # it is also used for detecting translations during foris_make_messages cmd
        section.add_field(
            Number, name="slices", label=_("Number of slices"), required=True,
            validators=validators.InRange(2, 15)
        )

        def form_cb(data):
            #res = current_state.backend.perform(
            #    "sample", "set_slices", {"slices": int(data["slices"])})

            ###
            SamplePluginConfigHandler.slices = int(data["slices"])

            res = {"result": True}
            ###

            return "save_result", res  # store {"result": ...} to be used in SamplePluginPage save() method

        form.add_callback(form_cb)
        return form


# This represents a plugin page
class SamplePluginPage(ConfigPageMixin, SamplePluginConfigHandler):
    menu_order = 90  # Where it should be placed in the main menu (higher the number the lower)
    template = "sample/sample"  # template which will be used (.html.js will be auto added)
    template_type = "jinja2"

    def get_backend_data(self):
        #data = current_state.backend.perform("sample", "list")
        ###
        import random
        res = {
            "records":
            enumerate([random.randint(0, 100) for _ in range(SamplePluginConfigHandler.slices)])
        }
        ###
        return res["records"]

    def save(self, *args, **kwargs):
        # Handle form result here
        return super(SamplePluginPage, self).save(*args, **kwargs)

    def _prepare_render_args(self, args):
        args['PLUGIN_NAME'] = SamplePlugin.PLUGIN_NAME
        args['PLUGIN_STYLES'] = SamplePlugin.PLUGIN_STYLES
        args['PLUGIN_STATIC_SCRIPTS'] = SamplePlugin.PLUGIN_STATIC_SCRIPTS
        args['PLUGIN_DYNAMIC_SCRIPTS'] = SamplePlugin.PLUGIN_DYNAMIC_SCRIPTS
        args['records'] = self.get_backend_data()

    def render(self, **kwargs):
        self._prepare_render_args(kwargs)
        return super(SamplePluginPage, self).render(**kwargs)

    def _action_get_records(self):
        # obtain and render the data and render a partial template (for ajax)
        records = self.get_backend_data()

        return bottle.template(
            "sample/_records.html.j2",
            records=records,
            template_adapter=bottle.Jinja2Template,
        )

    def call_ajax_action(self, action):
        if action == "get_records":
            return self._action_get_records()

        raise ValueError("Unknown AJAX action.")


# plugin definition
class SamplePlugin(ForisPlugin):
    PLUGIN_NAME = "sample"  # also shown in the url
    DIRNAME = os.path.dirname(os.path.abspath(__file__))

    PLUGIN_STYLES = [
        "css/sample.css",  # path to css script generated using sass/sample.sass
    ]
    PLUGIN_STATIC_SCRIPTS = [
        "js/contrib/Chart.bundle.min.js",  # 3rd party static js
        "js/sample.js",  # static js file
    ]
    PLUGIN_DYNAMIC_SCRIPTS = [
        "sample.js",  # dynamic js file (a template which will be rendered to javascript)
    ]

    def __init__(self, app):
        super(SamplePlugin, self).__init__(app)
        add_config_page("sample", SamplePluginPage, top_level=True)
