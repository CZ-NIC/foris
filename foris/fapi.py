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

from collections import defaultdict, OrderedDict
import copy
import logging

from bottle import MultiDict

from form import Input, InputWithArgs, Dropdown, Form, Checkbox, websafe, Hidden, Radio
from utils import Lazy
import validators as validators_module


logger = logging.getLogger(__name__)


class ForisFormElement(object):
    def __init__(self, name):
        self.name = name
        self.children = OrderedDict()
        self.parent = None

    def __iter__(self):
        for name in self.children:
            yield self.children[name]

    def _add(self, child):
        self.children[child.name] = child
        child.parent = self
        return child

    def _remove(self, child):
        del self.children[child.name]
        child.parent = None

    @property
    def sections(self):
        filtered = filter(lambda x: isinstance(x, Section), self.children.itervalues())
        return filtered


class ForisForm(ForisFormElement):
    def __init__(self, name, data=None):
        """

        :param name:
        :param data: data from request
        :type filter: Element
        :return:
        """
        super(ForisForm, self).__init__(name)
        if isinstance(data, MultiDict):
            self._request_data = {}  # values from request
            # convert MultiDict to normal dict with multiple values in lists
            # if value is suffixed with '[]' (i.e. it is multifield)
            for key, value in data.iteritems():
                if key.endswith("[]"):
                    # we don't want to alter lists in MultiDict instance
                    values = copy.deepcopy(data.getall(key))
                    logger.debug("%s: %s (%s)", key, values, value)
                    # split value by \r\n - sent by textarea
                    if "\r\n" in value:
                        values = value.split("\r\n")
                    # remove dummy value from hidden field
                    elif len(values) and not values[0]:
                        del values[0]
                    # strip [] suffix
                    self._request_data[key[:-2]] = values
                else:
                    self._request_data[key] = value
        else:
            self._request_data = data or {}
        self.defaults = {}  # default values from field definitions
        self.__data_cache = None  # cached data
        self.__form_cache = None
        self.validated = False
        self.requirement_map = defaultdict(list)  # mapping: requirement -> list of required_by
        self.callbacks = []
        self.callback_results = {}  # name -> result

    @property
    def data(self):
        """
        Current data, from defaults and request data.
        Caches the result on the first call.

        :return: dictionary with the Form's data
        """
        if self.__data_cache is None:
            self.__data_cache = self.current_data
        return self.__data_cache

    @property
    def current_data(self):
        """
        Current data, from defaults and request data.
        Does not use caching.

        :return: dictionary with the Form's data
        """
        data = {}
        logger.debug("Updating with defaults: %s", self.defaults)
        data.update(self.defaults)
        logger.debug("Updating with data: %s", dict(self._request_data))
        data.update(self._request_data)
        if data:
            data = self.clean_data(data)
        return data

    def clean_data(self, data):
        new_data = {}
        fields = self._get_all_fields()
        for field in fields:
            new_data[field.name] = data[field.name]
            if field.name in data:
                if issubclass(field.type, Checkbox):
                    # coerce checkbox values to boolean
                    new_data[field.name] = False if data[field.name] == "0" else bool(data[field.name])
        # get names of active fields according to new_data
        active_field_names = map(lambda x: x.name, self.get_active_fields(data=new_data))
        # get new dict of data of active fields
        return {k: v for k, v in new_data.iteritems() if k in active_field_names}

    def invalidate_data(self):
        self.__data_cache = None

    @property
    def _form(self):
        if self.__form_cache is not None:
            return self.__form_cache
        inputs = map(lambda x: x.field, self.get_active_fields())
        # TODO: creating the form everytime might by a wrong approach...
        logger.debug("Creating Form()...")
        form = Form(*inputs)
        form.fill(self.data)
        self.__form_cache = form
        return form

    @property
    def valid(self):
        return self._form.valid

    def _get_all_fields(self, element=None, fields=None):
        element = element or self
        fields = fields or []
        for c in element.children.itervalues():
            if c.children:
                fields = self._get_all_fields(c, fields)
            if isinstance(c, Field):
                fields.append(c)
        return fields

    def get_active_fields(self, element=None, data=None):
        """Get all fields that meet their requirements.

        :param element:
        :param data: data to check requirements against
        :return: list of fields
        """
        fields = self._get_all_fields(element)
        if fields:
            data = data or self.data
        return filter(lambda f: f.has_requirements(data), fields)

    def add_section(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return: new Section
        :rtype: Section
        """
        if len(args) and isinstance(args[0], Section):
            return self._add(args[0])
        return self._add(Section(self, *args, **kwargs))

    @property
    def active_fields(self):
        return self.get_active_fields()

    @property
    def errors(self):
        return self._form.note

    def render(self):
        result = "<div class=\"errors\">%s</div>" % self.errors
        result += "\n".join(c.render() for c in self.children.itervalues())
        return result

    def save(self):
        self.process_callbacks(self.data)

    def validate(self):
        self.validated = True
        return self._form.validates(self.data)

    def add_callback(self, cb):
        """Add callback function.

        Callback is a function taking argument `data` (contains form data) and returning
        a tuple `(action, *args)`.
        Action can be one of following:
            - save_result: arg[0] is dict of result_name->result - results are saved to
                           dictionary callback_results (instance attribute)
                           ValueError is raised when two callbacks use same result_name
            - none: do nothing, everything has been processed in the callback function

        :param cb: callback function
        :return: None
        """
        self.callbacks.append(cb)

    def process_callbacks(self, form_data):
        logger.debug("Processing callbacks")
        for cb in self.callbacks:
            logger.debug("Processing callback: %s", cb)
            cb_result = cb(form_data)
            operation = cb_result[0]
            if operation == "none":
                pass
            elif operation == "save_result":
                for k, v in cb_result[1].iteritems():
                    if k in self.callback_results:
                        raise ValueError("save_result callback returned result with duplicate name: '%s'" % k)
                    self.callback_results[k] = v
            else:
                raise NotImplementedError("Unsupported callback operation: %s" % operation)


class Section(ForisFormElement):
    def __init__(self, main_form, name, title, description=None):
        super(Section, self).__init__(name)
        self._main_form = main_form
        self.name = name
        self.title = title
        self.description = description

    @property
    def active_fields(self):
        return self._main_form.get_active_fields(self)

    def add_field(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        :rtype: Field
        """
        if len(args) and isinstance(args[0], Field):
            return self._add(args[0])
        return self._add(Field(self._main_form, *args, **kwargs))

    def add_section(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return: new Section
        :rtype: Section
        """
        if len(args) and isinstance(args[0], Section):
            return self._add(args[0])
        return self._add(Section(self._main_form, *args, **kwargs))

    def render(self):
        content = "\n".join(c.render() for c in self.children.itervalues()
                            if c.has_requirements(self._main_form.data))
        return "<section>\n<h2>%(title)s</h2>\n<p>%(description)s</p>\n%(content)s\n</section>" \
               % dict(title=self.title, description=self.description, content=content)


class Field(ForisFormElement):
    def __init__(
        self, main_form, type, name, label=None, required=False, preproc=None, validators=None,
        hint="", multifield=False, **kwargs
    ):
        """

        :param main_form: parent form of this field
        :type main_form: ForisForm
        :param type: type of field
        :param name: field name (rendered also as HTML name attribute)
        :param label: display name of field
        :param required: True if field is mandatory
        :param preproc: function to preprocess the value
        :type preproc: callable
        :param validators: validator or list of validators
        :type validators: validator or list
        :param hint: short descriptive text explaining the purpose of the field
        :param multifield: whether multiple values can be returned
        :param kwargs: passed to Input constructor
        """
        super(Field, self).__init__(name)
        #
        self.type = type
        self.name = name
        self.preproc = preproc
        if validators and not isinstance(validators, list):
            validators = [validators]
        self.validators = validators or []
        if not all(map(lambda x: isinstance(x, validators_module.Validator), self.validators)):
            raise TypeError("Argument 'validators' must be Validator instance or list of them.")
        self._kwargs = kwargs
        self.required = required
        if self.required:
            self.validators.append(validators_module.NotEmpty())
        self._kwargs["required"] = self.required
        self._kwargs["description"] = label
        self.requirements = {}
        self.hint = hint
        self.multifield = multifield
        default = kwargs.pop("default", [] if self.multifield else None)
        if issubclass(self.type, Checkbox):
            self._kwargs["value"] = "1"  # we need a non-empty value here
            self._kwargs["checked"] = False if default == "0" else bool(default)
        # set defaults for main form
        self._main_form = main_form
        self._main_form.defaults.setdefault(name, default)
        # cache for rendered field - remove after finishing TODO #2793
        self.__field_cache = None

    def __str__(self):
        return self.render()

    def _generate_html_classes(self):
        classes = []
        if self.name in self._main_form.requirement_map:
            classes.append("has-requirements")
        return classes

    def _generate_html_data(self):
        return validators_module.validators_as_data_dict(self.validators)

    @property
    def field(self):
        if self.__field_cache is not None:
            return self.__field_cache
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
        # multifield magic
        rendered_name = self.name
        if self.multifield:
            # '[]' suffix is used for internal magic
            # it is stripped when ForisForm is preparing data
            rendered_name = self.name + "[]"
            if issubclass(self.type, Dropdown):
                attrs["multiple"] = "multiple"
        # call the proper constructor (web.py Form API is not consistent in this)
        if issubclass(self.type, InputWithArgs):
            args = attrs.pop("args", ())
            # InputWithArgs - signature: def __init__(self, name, args, *validators, **attrs)
            field = self.type(rendered_name, args, *validators, **attrs)
        else:
            # other - signature: def __init__(self, name, *validators, **attrs)
            field = self.type(rendered_name, *validators, **attrs)
        if self._main_form.validated:
            field.validate(self._main_form.data or {}, self.name)
        else:
            field.set_value(self._main_form.data.get(self.name) or "")
        if field.note:
            field.attrs['class'] = " ".join(field.attrs['class'].split(" ") + ["field-validation-fail"])
        self.__field_cache = field
        return self.__field_cache

    @property
    def html_id(self):
        return self.field.id

    @property
    def label_tag(self):
        def create_label(text):
            if issubclass(self.type, Radio):
                label = "<label>%s</label>" % websafe(text)
            if issubclass(self.type, Input):
                label = "<label for=\"%s\">%s</label>"\
                        % (self.field.id, websafe(text))
            else:
                label = ""

            return label

        description = self.field.description

        return create_label(description)

    @property
    def errors(self):
        return self.field.note

    @property
    def hidden(self):
        return self.type is Hidden

    def render(self):
        return self.field.render()

    def requires(self, field, value=None):
        """Specify that field requires some other field
        (optionally having some value).

        `value` can be a callable, in that case, field's value
        will be passed as the first argument to that callable.

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
            # if the required value is a callable, pass the value as the first argument
            if callable(req_value):
                return req_value(data.get(req_name))
            # if the required value is not specified, consider as fulfilled,
            # otherwise compare required and current value
            result = result and True if req_value is None else data.get(req_name) == req_value
            if not result:
                return False
        return True
