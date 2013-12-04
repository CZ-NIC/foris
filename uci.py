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

from bottle import Bottle, request, view
import bottle
import logging
from form import Checkbox, Form, Textbox, websafe
from ncclient.operations import RPCError
from nuci import client
from nuci.client import edit_uci_config
from nuci.modules import uci_raw
from utils import print_model, login_required
from utils.bottle_csrf import CSRFPlugin
from validators import NotEmpty, RegExp


logger = logging.getLogger("foris.uci")


app = Bottle()
app.install(CSRFPlugin())


class UciRawForm(Form):
    def __init__(self, the_type, editable_key=True, **kw):
        inputs = []

        if the_type is uci_raw.Value:
            if editable_key:
                inputs.append(Textbox("index", RegExp("Index must be a number", r"\d+"), description="Value index"))
            inputs.append(Textbox("content", NotEmpty(), description="Value content"))
        elif the_type is uci_raw.Option:
            if editable_key:
                inputs.append(Textbox("name", NotEmpty(), description="Option name"))
            inputs.append(Textbox("value", NotEmpty(), description="Option value"))
        elif the_type is uci_raw.List:
            if editable_key:
                inputs.append(Textbox("name", NotEmpty(), description="List name"))
            inputs.append(Textbox("first_content", NotEmpty(), description="First value content"))
        elif the_type is uci_raw.Section:
            if editable_key:
                inputs.append(Textbox("name", description="Section name"))
            inputs.append(Textbox("type", NotEmpty(), description="Section type"))
            inputs.append(Checkbox("anonymous", description="Anonymous"))
        else:
            raise ValueError("Unable to create form for type '%s'" % the_type)

        self.model_type = the_type

        super(UciRawForm, self).__init__(*inputs, **kw)

    def fill_from_uci(self, uci_model):
        for input_ in self.inputs:
            try:
                input_value = getattr(uci_model, input_.name)  # TODO: catch AttributeError?
                input_.value = input_value
            except AttributeError:
                logger.error("Unable to bind: %s" % input_.name)

    def save_to_model(self, model):
        for input_ in self.inputs:
            setattr(model, input_.name, input_.value)

    def to_model(self):
        if self.valid:
            if self.model_type is uci_raw.List:
                # list needs to contain the first value, special handling follows
                list_ = uci_raw.List(self.d.name)
                list_.add(uci_raw.Value(1, self.d.first_content))
                return list_

            model = self.model_type(**{input_.name: input_.value for input_ in self.inputs})
        else:
            return None

        return model


app = Bottle()


@app.get("/", name="uci_index")
@view("uci/index")
@login_required
def index():
    uci_model = client.get_uci_config()
    node_path = request.GET.get("node")
    return dict(tree=uci_model, node=None,
                node_path=node_path.split(".") if node_path else None)


@app.get("/<node:re:\w+(\.\w+)*>/edit", name="uci_edit")
@view("uci/edit")
@login_required
def edit(node):
    uci_model = client.get_uci_config()
    node_model = uci_model.find_child(node)

    form = UciRawForm(type(node_model), editable_key=False)
    form.fill_from_uci(node_model)

    return dict(form=form, node_path=node)


@app.post("/<node:re:\w+(\.\w+)*>/edit")
@view("uci/edit")
@login_required
def edit_post(node):
    uci_model = client.get_uci_config()
    node_model = uci_model.find_child(node)

    form = UciRawForm(type(node_model), editable_key=False)
    if form.validates(request.POST):
        form.save_to_model(node_model)
        edit_uci_config(node_model)
        bottle.redirect("/uci/?done")

    return dict(form=form, node_path=node)


@app.get("/<node:re:\w+(\.\w+)*>/create", name="uci_create")
@view("uci/edit")
@login_required
def create(node):
    operation = request.GET.get("operation")
    uci_model = client.get_uci_config()
    node_model = uci_model.find_child(node)
    if type(node_model) is uci_raw.Section:
        # Section contains lists or options
        if operation == "add-list":
            form = UciRawForm(uci_raw.List, editable_key=True)
        elif operation == "add-option":
            form = UciRawForm(uci_raw.Option, editable_key=True)
        else:
            raise ValueError("Requested operation not allowed for Section node.")
    elif type(node_model) is uci_raw.Config:
        # Config consists of Sections
        form = UciRawForm(uci_raw.Section, editable_key=True)
    elif type(node_model) is uci_raw.List:
        # List consists of Values
        form = UciRawForm(uci_raw.Value, editable_key=True)
    else:
        raise ValueError("New node cannot be created here.")

    return dict(node_path=node, form=form)


@app.post("/<node:re:\w+(\.\w+)*>/create")
@view("uci/edit")
@login_required
def create_post(node):
    operation = request.GET.get("operation")
    uci_model = client.get_uci_config()
    parent = uci_model.find_child(node)
    if isinstance(parent, uci_raw.Section):
        if operation == "add-list":
            form = UciRawForm(uci_raw.List, editable_key=True)
            if form.validates(request.POST):
                new_element = form.to_model()
        elif operation == "add-option":
            form = UciRawForm(uci_raw.Option, editable_key=True)
            if form.validates(request.POST):
                new_element = form.to_model()
        else:
            raise ValueError("Requested operation not allowed for Section node.")
    elif isinstance(parent, uci_raw.Config):
        form = UciRawForm(uci_raw.Section, editable_key=True)(request.POST)
        if form.validates(request.POST):
            new_element = form.to_model()
    elif isinstance(parent, uci_raw.List):
        form = UciRawForm(uci_raw.Value, editable_key=True)(request.POST)
        if form.validates(request.POST):
            new_element = form.to_model()
    else:
        raise ValueError("New node cannot be created here.")

    if not form.valid:
        return dict(node_path=node, form=form)

    new_element.operation = "create"
    parent.add(new_element)
    print_model(new_element)
    edit_uci_config(new_element)
    bottle.redirect("/uci/")


@app.get("/<node:re:\w+(\.\w+)*>/remove", name="uci_remove")
@login_required
def remove(node):
    uci_model = client.get_uci_config()
    node_model = uci_model.find_child(node)
    node_model.operation = "remove"
    try:
        edit_uci_config(node_model)
        bottle.redirect("/uci/?done")
    except RPCError, e:
        logger.error(e.message)
    bottle.redirect("/uci/?error")


@app.get("/<node:re:\w+(\.\w+)*>/debug", name="uci_debug")
@login_required
def debug(node):
    uci_model = client.get_uci_config()
    node_model = uci_model.find_child(node)
    return "<pre>%s</pre>" % websafe(print_model(node_model))