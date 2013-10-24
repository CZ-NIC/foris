from collections import defaultdict
from form import Dropdown, Form, Checkbox, websafe
from nuci import client
import logging
from nuci.configurator import add_config_update, commit
from utils import Lazy
import validators as validators_module


logger = logging.getLogger("kapi")


class KruciFormElement(object):
    def __init__(self):
        self.children = []
        self.parent = None
        self.callbacks = []

    def _add(self, child):
        self.children.append(child)
        child.parent = self
        return child

    def _remove(self, child):
        self.children.remove(child)
        child.parent = None


class KruciForm(KruciFormElement):
    def __init__(self, name, data=None, filter=None):
        """

        :param name:
        :param data: data from request
        :param filter: subtree filter for nuci config
        :type filter: Element
        :return:
        """
        super(KruciForm, self).__init__()
        self.name = name
        self._request_data = data or {}  # values from request
        self._nuci_data = {}  # values fetched from nuci
        self.defaults = {}  # default values from field definitions
        self.__data_cache = None  # cached data
        self.__form_cache = None
        self.validators = []
        self._validated = False
        # _nuci_config is not required every time, lazy-evaluate it
        self._nuci_config = Lazy(lambda: client.get(filter))
        self.requirement_map = defaultdict(list)  # mapping: requirement -> list of required_by

    @property
    def data(self):
        """
        Data are union of defaults + nuci values + request data.

        :return: currently known form data
        """
        if self.__data_cache is not None:
            return self.__data_cache
        self._update_nuci_data()
        data = {}
        logger.debug("Updating with defaults: %s" % self.defaults)
        data.update(self.defaults)
        logger.debug("Updating with Nuci data: %s" % self._nuci_data)
        data.update(self._nuci_data)
        logger.debug("Updating with data: %s" % dict(self._request_data))
        data.update(self._request_data)
        data = self.clean_data(data)
        self.__data_cache = data
        return data

    def clean_data(self, data):
        fields = self._get_all_fields()
        for field in fields:
            if field.name in data:
                if issubclass(field.type, Checkbox):
                    # coerce checkbox values to boolean
                    data[field.name] = False if data[field.name] == "0" else bool(data[field.name])
        return data

    def invalidate_data(self):
        self.__data_cache = None

    @property
    def _form(self):
        if self.__form_cache is not None:
            return self.__form_cache
        inputs = map(lambda x: x.form_input, self._get_active_fields())
        # TODO: creating the form everytime might by a wrong approach...
        logger.debug("Creating Form()...")
        form = Form(*inputs)
        form.validators = self.validators
        form.fill(self.data)
        self.__form_cache = form
        return form

    @property
    def valid(self):
        return self._form.valid

    def _get_all_fields(self, element=None, fields=None):
        element = element or self
        fields = fields or []
        for c in element.children:
            if c.children:
                fields = self._get_all_fields(c, fields)
            if isinstance(c, Field):
                fields.append(c)
        return fields

    def _get_active_fields(self, element=None):
        """Get all descendant fields that meet their requirements.

        :param element:
        :return: list of fields
        """
        fields = self._get_all_fields(element)
        return filter(lambda f: f.has_requirements(self.data), fields)

    def _update_nuci_data(self):
        for field in self._get_all_fields():
            if field.nuci_path:
                value = self._nuci_config.find_child(field.nuci_path)
                if value:
                    self._nuci_data[field.name] = field.nuci_preproc(value)
            elif field.nuci_path:
                NotImplementedError("Cannot map value from Nuci: '%s'" % field.nuci_path)

    def add_section(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return: new Section
        :rtype: Section
        """
        return self._add(Section(self, *args, **kwargs))

    def add_validator(self, validator):
        self.validators.append(validator)

    def render(self):
        data = self.data
        result = "<div class=\"errors\">%s</div>" % self._form.note
        result += "\n".join(c.render(data, validate=self._validated) for c in self.children)
        return result
        #return self._form.render()

    def save(self):
        self.process_callbacks(self.data)
        commit()

    def validate(self):
        self._validated = True
        return self._form.validates(self.data)

    def add_callback(self, cb):
        """Add callback function.

        Callback is a function taking argument `data` (contains form data) and returning
        a tuple `(action, *args)`.
        Action can be one of following:
            - edit_config: args is Uci instance - send command for modifying Uci structure
            - none: do nothing, everything has been processed in the callback function

        :param cb: callback function
        :return: None
        """
        self.callbacks.append(cb)

    def process_callbacks(self, form_data):
        logger.debug("Processing callbacks")
        for cb in self.callbacks:
            logger.debug("Processing callback: %s" % cb)
            cb_result = cb(form_data)
            operation = cb_result[0]
            if operation == "none":
                return
            data = cb_result[1:] if len(cb_result) > 1 else ()
            if operation == "edit_config":
                add_config_update(*data)
            else:
                raise NotImplementedError("Unsupported callback operation: %s" % operation)


class Section(KruciFormElement):
    def __init__(self, main_form, name, title, description=None):
        super(Section, self).__init__()
        self._main_form = main_form
        self.name = name
        self.title = title
        self.description = description

    def add_field(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        :rtype: Field
        """
        return self._add(Field(self._main_form, *args, **kwargs))

    def add_section(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return: new Section
        :rtype: Section
        """
        return self._add(Section(self._main_form, *args, **kwargs))

    def render(self, data, validate=False):
        content = "\n".join(c.render(data, validate=validate) for c in self.children
                            if c.has_requirements(data))
        return "<section>\n<h2>%(title)s</h2>\n<p>%(description)s</p>\n%(content)s\n</section>" \
               % dict(title=self.title, description=self.description, content=content)


class Field(KruciFormElement):
    def __init__(self, main_form, type, name, label=None, required=False, callback=None, nuci_path=None,
                 nuci_preproc=lambda val: val.value, validators=None, **kwargs):
        """

        :param main_form: parent form of this field
        :type main_form: KruciForm
        :param type: type of field
        :param name: field name (rendered also as HTML name attribute)
        :param label: display name of field
        :param required: True if field is mandatory
        :param callback: callback for saving the field
        :param nuci_path: path in Nuci get response
        :param nuci_preproc: function to process raw YinElement instance, returns field value
        :type nuci_preproc: callable
        :param validators: validator or list of validators
        :type validators: validator or list
        :param kwargs: passed to Input constructor
        """
        super(Field, self).__init__()
        #
        self.type = type
        self.name = name
        self.callback = callback
        self.nuci_path = nuci_path
        self.nuci_preproc = nuci_preproc
        if validators and not isinstance(validators, list):
            validators = [validators]
        self.validators = validators or []
        self._kwargs = kwargs
        self.required = required
        if self.required:
            self.validators.append(validators_module.NotEmpty())
        self._kwargs["required"] = self.required
        self._kwargs["description"] = label
        self.requirements = {}
        default = kwargs.pop("default", None)
        if issubclass(self.type, Checkbox):
            self._kwargs["value"] = "1"  # we need a non-empty value here
            self._kwargs["checked"] = False if default == "0" else bool(default)
        # set defaults for main form
        self._main_form = main_form
        self._main_form.defaults.setdefault(name, default)

    def _generate_html_classes(self):
        classes = []
        if self.name in self._main_form.requirement_map:
            classes.append("has-requirements")
        if self.required:
            classes.append("required")
        if len(self.validators) > 0:
            classes.append("validate")
        return classes

    def _generate_html_data(self):
        data = {}
        validators = []
        for v in self.validators:
            if v.js_validator:
                validators.append("%s" % v.js_validator)
                params = v.js_validator_params
                logger.warning("%s" % v)
                logger.warning("%s" % params)
                if params:
                    data['validator-%s' % v.js_validator] = params
        if validators:
            data['validators'] = " ".join(validators)
        return data

    @property
    def form_input(self):
        validators = self.validators
        # beware, altering self._kwargs might cause funky behaviour
        attrs = self._kwargs.copy()
        # get defined and add generated HTML classes
        classes = attrs.pop("class", "")
        classes = classes.split(" ")
        classes.extend(self._generate_html_classes())
        if classes:
            attrs['class'] = " ".join(classes)
        # append HTML data
        html_data = self._generate_html_data()
        for key, value in html_data.iteritems():
            attrs['data-%s' % key] = value
        # call the proper constructor (web.py Form API is not consistent in this)
        if issubclass(self.type, Dropdown):
            args = attrs.pop("args", ())
            # Dropdowns - signature: def __init__(self, name, args, *validators, **attrs)
            return self.type(self.name, args, *validators, **attrs)
        # other - signature: def __init__(self, name, *validators, **attrs)
        return self.type(self.name, *validators, **attrs)

    def render(self, data, validate=False):
        result = []
        inp = self.form_input
        if validate:
            inp.validate(data.get(self.name) or "")
        else:
            inp.set_value(data.get(self.name) or "")
        if not inp.is_hidden():
            result.append('<label for="%s">%s</label>' % (inp.id, websafe(inp.description)))
        result.append(inp.pre)
        result.append(inp.render())
        if inp.note:
            result.append("<span class=\"error\">%s</span>" % inp.note)
        result.append(inp.post)
        result.append("\n")
        return ''.join(result)

    def requires(self, field, value=None):
        """Specify that field requires some other field
        (optionally having some value).

        :param field: name of required field
        :param value: exact value of field
        :return: self
        """
        self._main_form.requirement_map[field].append(self.name)
        self.requirements[field] = value
        return self

    def has_requirements(self, data):
        """Check that this element has its requirements filled in data.

        :param data:
        :return: False if requirements are not met, True otherwise
        """
        for req_name, req_value in self.requirements.iteritems():
            # requirement exists
            result = req_name in data
            # requirement has defined value (value of None is ignored, thus result is True)
            result = result and True if req_value is None else data.get(req_name) == req_value
            if not result:
                return False
        return True