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

"""
HTML forms, based on part of web.py with some customizations.

Currently, it is used in Foris for rendering and validating forms.
It might be replaced by our own solution in future, or get changed
heavily to suit our needs...

Current major changes:

- validators are moved to a separate file, every validator is a class with same interface
- checkboxes are rendered together with a hidden field with same name, so a "0" is
  sent when the form is submitted even if the checkbox is not checked (bit a hack)
- field is validated only if it's non-empty and Field.required is True (Field.required is
  also a new attribute)
- Form.render() and Form.render_css() is not used anymore and throws NotImplementedError,
  Form fields should be rendered by FAPI
- TODO: change signature of Field constructors, make it consistent (see Input vs. Dropdown)
- HTML ID for inputs is mangled according to module variable ID_TEMPLATE

web.py is originally licensed under public domain
"""

import copy
import itertools


ID_TEMPLATE = "field-%s"
# template for field IDs - gets one "%s" formatting argument

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.

        >>> o = storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        Traceback (most recent call last):
            ...
        AttributeError: 'a'

    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            raise AttributeError, k

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'


storage = Storage


def safeunicode(obj, encoding='utf-8'):
    r"""
    Converts any given object to unicode string.

        >>> safeunicode('hello')
        u'hello'
        >>> safeunicode(2)
        u'2'
        >>> safeunicode('\xe1\x88\xb4')
        u'\u1234'
    """
    t = type(obj)
    if t is unicode:
        return obj
    elif t is str:
        return obj.decode(encoding)
    elif t in [int, float, bool]:
        return unicode(obj)
    elif hasattr(obj, '__unicode__') or isinstance(obj, unicode):
        return unicode(obj)
    else:
        return str(obj).decode(encoding)


def safestr(obj, encoding='utf-8'):
    r"""
    Converts any given object to utf-8 encoded string.

        >>> safestr('hello')
        'hello'
        >>> safestr(u'\u1234')
        '\xe1\x88\xb4'
        >>> safestr(2)
        '2'
    """
    if isinstance(obj, unicode):
        return obj.encode(encoding)
    elif isinstance(obj, str):
        return obj
    elif hasattr(obj, 'next'): # iterator
        return itertools.imap(safestr, obj)
    else:
        return str(obj)


def htmlquote(text):
    r"""
Encodes `text` for raw use in HTML.
>>> htmlquote(u"<'&\">")
u'&lt;&#39;&amp;&quot;&gt;'
"""
    text = text.replace(u"&", u"&amp;") # Must be done first!
    text = text.replace(u"<", u"&lt;")
    text = text.replace(u">", u"&gt;")
    text = text.replace(u"'", u"&#39;")
    text = text.replace(u'"', u"&quot;")
    return text


def websafe(val):
    r"""Converts `val` so that it is safe for use in Unicode HTML.

>>> websafe("<'&\">")
u'&lt;&#39;&amp;&quot;&gt;'
>>> websafe(None)
u''
>>> websafe(u'\u203d')
u'\u203d'
>>> websafe('\xe2\x80\xbd')
u'\u203d'
"""
    if val is None:
        return u''
    elif isinstance(val, str):
        val = val.decode('utf-8')
    elif not isinstance(val, unicode):
        val = unicode(val)

    return htmlquote(val)

#######################

def attrget(obj, attr, value=None):
    try:
        if hasattr(obj, 'has_key') and obj.has_key(attr):
            return obj[attr]
    except TypeError:
        # Handle the case where has_key takes different number of arguments.
        # This is the case with Model objects on appengine. See #134
        pass
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return value


class Form(object):
    r"""
    HTML form.

        >>> f = Form(Textbox("x"))
        >>> f.render()
        u'<table>\n    <tr><th><label for="field-x">x</label></th><td><input type="text" id="field-x" name="x"/></td></tr>\n</table>'
    """

    def __init__(self, *inputs, **kw):
        self.inputs = inputs
        self.valid = True
        self.note = None
        self.validators = kw.pop('validators', [])

    def __call__(self, x=None):
        o = copy.deepcopy(self)
        if x: o.validates(x)
        return o

    def render(self):
        out = ''
        out += self.rendernote(self.note)
        out += '<table>\n'

        for i in self.inputs:
            html = safeunicode(i.pre) + i.render() + self.rendernote(i.note) + safeunicode(i.post)
            if i.is_hidden():
                out += '    <tr style="display: none;"><th></th><td>%s</td></tr>\n' % (html)
            else:
                out += '    <tr><th><label for="%s">%s</label></th><td>%s</td></tr>\n' % (
                i.id, websafe(i.description), html)
        out += "</table>"
        return out

    def render_css(self):
        #out = []
        #out.append(self.rendernote(self.note))
        #for i in self.inputs:
        #    if not i.is_hidden():
        #        out.append('<label for="%s">%s</label>' % (i.id, websafe(i.description)))
        #    out.append(i.pre)
        #    out.append(i.render())
        #    out.append(self.rendernote(i.note))
        #    out.append(i.post)
        #    out.append('\n')
        #return ''.join(out)
        raise NotImplementedError()

    def rendernote(self, note):
        if note:
            return '<strong class="wrong">%s</strong>' % websafe(note)
        else:
            return ""

    def validates(self, source=None, _validate=True, **kw):
        source = source or kw
        out = True
        for i in self.inputs:
            if _validate:
                out = i.validate(source) and out
            else:
                i.set_value(attrget(source, i.name))
        if _validate:
            out = out and self._validate(source)
            self.valid = out
        return out

    def _validate(self, value):
        self.value = value
        for v in self.validators:
            if not v.valid(value):
                self.note = v.msg
                return False
        return True

    def fill(self, source=None, **kw):
        return self.validates(source, _validate=False, **kw)

    def __getitem__(self, i):
        for x in self.inputs:
            if x.name == i: return x
        raise KeyError, i

    def __getattr__(self, name):
        # don't interfere with deepcopy
        inputs = self.__dict__.get('inputs') or []
        for x in inputs:
            if x.name == name: return x
        raise AttributeError, name

    def get(self, i, default=None):
        try:
            return self[i]
        except KeyError:
            return default

    def _get_d(self): #@@ should really be form.attr, no?
        return storage([(i.name, i.get_value()) for i in self.inputs])

    d = property(_get_d)


class Input(object):
    def __init__(self, name, *validators, **attrs):
        self.name = name
        self.validators = validators
        self.attrs = attrs = AttributeList(attrs)

        self.description = attrs.pop('description', name)
        self.value = attrs.pop('value', None)
        self.pre = attrs.pop('pre', "")
        self.post = attrs.pop('post', "")
        self.note = None
        self.required = attrs.pop('required', False)
        if self.required is True:
            attrs['required'] = "required"

        self.id = attrs.setdefault('id', self.get_default_id())

        if 'class_' in attrs:
            attrs['class'] = attrs['class_']
            del attrs['class_']

    def is_hidden(self):
        return False

    def get_type(self):
        raise NotImplementedError

    def get_default_id(self):
        return ID_TEMPLATE % self.name

    def validate(self, source, field_name=None):
        value = attrget(source, field_name or self.name)
        self.set_value(value)
        if not self.required and value == "":
            return True
        for v in self.validators:
            if not v.valid(source if v.validate_with_context else value):
                self.note = v.msg
                return False
        return True

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = self.get_type()
        if self.value is not None:
            attrs['value'] = self.value
        attrs['name'] = self.name

        return ('<input %s></input>' % (attrs)) + self.render_extra_after

    @property
    def render_extra_after(self):
        return ""

    def rendernote(self, note):
        if note:
            return '<strong class="wrong">%s</strong>' % websafe(note)
        else:
            return ""

    def addatts(self):
        # add leading space for backward-compatibility
        return " " + str(self.attrs)

    def __str__(self):
        self.render()


class AttributeList(dict):
    """List of atributes.

    >>> a = AttributeList(type='text', name='x', value=20)
    >>> a
    <attrs: 'type="text" name="x" value="20"'>
    """

    def copy(self):
        return AttributeList(self)

    def __str__(self):
        return " ".join(['%s="%s"' % (k, websafe(v)) for k, v in self.items()])

    def __repr__(self):
        return '<attrs: %s>' % repr(str(self))


class Textbox(Input):
    """Textbox input.

        >>> Textbox(name='foo', value='bar').render()
        u'<input type="text" id="field-foo" value="bar" name="foo"/>'
        >>> Textbox(name='foo', value=0).render()
        u'<input type="text" id="field-foo" value="0" name="foo"/>'
    """

    def get_type(self):
        return 'text'


class Password(Input):
    """Password input.

        >>> Password(name='password', value='secret').render()
        u'<input type="password" id="field-password" value="secret" name="password"/>'
    """

    def get_type(self):
        return 'password'


class PasswordWithHide(Password):
    @property
    def render_extra_after(self):
        return "<span class='password-toggle'><i class='fas fa-eye'></i></span>"


class Number(Input):
    """Number input.

        >>> Number(name='number', value='123').render()
        u'<input type="number" id="field-number" value="123" name="number"/>'
    """

    def get_type(self):
        return 'number'


class Email(Input):
    """Email input.

        >>> Email(name='email', value='mail@example.com').render()
        u'<input type="email" id="field-email" value="mail@example.com" name="email"/>'
    """

    def get_type(self):
        return 'email'


class Time(Input):
    """Password input.

        >>> Time(name='time', value='11:22').render()
        u'<input type="time" id="field-time" value="11:22" name="time"/>'
    """

    def get_type(self):
        return 'time'


class Textarea(Input):
    """Textarea input.

        >>> Textarea(name='foo', value='bar').render()
        u'<textarea id="field-foo" name="foo">bar</textarea>'
    """

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        value = websafe(self.value or '')
        return '<textarea %s>%s</textarea>' % (attrs, value)


class InputWithArgs(Input):
    def __init__(self, name, args, *validators, **attrs):
        if isinstance(args, dict):
            args = args.items()
        self.args = args
        super(InputWithArgs, self).__init__(name, *validators, **attrs)


class Dropdown(InputWithArgs):
    r"""Dropdown/select input.

        >>> Dropdown(name='foo', args=['a', 'b', 'c'], value='b').render()
        u'<input type="hidden" name="foo" value=""><select id="field-foo" name="foo">\n  <option value="a">a</option>\n  <option selected="selected" value="b">b</option>\n  <option value="c">c</option>\n</select>\n'
        >>> Dropdown(name='foo', args=[('a', 'aa'), ('b', 'bb'), ('c', 'cc')], value='b').render()
        u'<input type="hidden" name="foo" value=""><select id="field-foo" name="foo">\n  <option value="a">aa</option>\n  <option selected="selected" value="b">bb</option>\n  <option value="c">cc</option>\n</select>\n'
    """

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        # dummy value to post when no item is selected
        x = '<input type="hidden" name="%s" value="">' % self.name
        x += '<select %s>\n' % attrs

        for arg in self.args:
            x += self._render_option(arg)

        x += '</select>\n'
        return x

    def _render_option(self, arg, indent='  '):
        if isinstance(arg, (tuple, list)):
            value, desc = arg
        else:
            value, desc = arg, arg

        if self.value == value or (isinstance(self.value, list) and value in self.value):
            select_p = ' selected="selected"'
        else:
            select_p = ''
        return indent + '<option%s value="%s">%s</option>\n' % (
        select_p, websafe(value), websafe(desc))


class GroupedDropdown(Dropdown):
    r"""Grouped Dropdown/select input.

        >>> GroupedDropdown(name='car_type', args=(('Swedish Cars', ('Volvo', 'Saab')), ('German Cars', ('Mercedes', 'Audi'))), value='Audi').render()
        u'<input type="hidden" name="car_type" value=""><select id="field-car_type" name="car_type">\n  <optgroup label="Swedish Cars">\n    <option value="Volvo">Volvo</option>\n    <option value="Saab">Saab</option>\n  </optgroup>\n  <optgroup label="German Cars">\n    <option value="Mercedes">Mercedes</option>\n    <option selected="selected" value="Audi">Audi</option>\n  </optgroup>\n</select>\n'
        >>> GroupedDropdown(name='car_type', args=(('Swedish Cars', (('v', 'Volvo'), ('s', 'Saab'))), ('German Cars', (('m', 'Mercedes'), ('a', 'Audi')))), value='a').render()
        u'<input type="hidden" name="car_type" value=""><select id="field-car_type" name="car_type">\n  <optgroup label="Swedish Cars">\n    <option value="v">Volvo</option>\n    <option value="s">Saab</option>\n  </optgroup>\n  <optgroup label="German Cars">\n    <option value="m">Mercedes</option>\n    <option selected="selected" value="a">Audi</option>\n  </optgroup>\n</select>\n'

    """

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name

        x = '<input type="hidden" name="%s" value="">' % self.name
        x += '<select %s>\n' % attrs

        for label, options in self.args:
            x += '  <optgroup label="%s">\n' % websafe(label)
            for arg in options:
                x += self._render_option(arg, indent='    ')
            x += '  </optgroup>\n'

        x += '</select>\n'
        return x


class Radio(Input):
    def __init__(self, name, args, *validators, **attrs):
        self.args = args
        super(Radio, self).__init__(name, *validators, **attrs)

    def get_default_id(self):
        return ID_TEMPLATE % self.name + '_%s'

    def render(self):
        rendered = []
        for arg in self.args:
            if isinstance(arg, (tuple, list)):
                value, desc = arg
            else:
                value, desc = arg, arg
            attrs = self.attrs.copy()
            rendered_input = RadioSingle.render_single(value, self.name, self.value, attrs)
            rendered.append(
                '<label for="%s">%s %s</label>' % (attrs['id'], rendered_input, websafe(desc))
            )
        return '<div class="radio-inputs">%s</div>' % "\n".join(rendered)


class RadioSingle(Input):
    def __init__(self, name, *validators, **attrs):
        self.name = name
        self.group = attrs.pop("group", name)
        super(RadioSingle, self).__init__(name, *validators, **attrs)
        self.id = self.id % self.name

    def get_default_id(self):
        return ID_TEMPLATE % self.group + '_%s'

    @staticmethod
    def render_single(name, group, current_value, attrs):
        attrs['id'] = attrs['id'] % safestr(name or "")
        attrs['name'] = group
        attrs['type'] = 'radio'
        attrs['value'] = name
        if current_value == attrs['value']:
            attrs['checked'] = 'checked'

        return '<input %s />' % attrs

    def render(self):
        return RadioSingle.render_single(
            self.name, self.group, self.value, self.attrs)


class Checkbox(Input):
    """Checkbox input.

    >>> Checkbox('foo', value='bar', checked=True).render()
    u'<input type="hidden" name="foo" value="0"><input checked="checked" type="checkbox" id="field-foo_bar" value="bar" name="foo"/>'
    >>> Checkbox('foo', value='bar').render()
    u'<input type="hidden" name="foo" value="0"><input type="checkbox" id="field-foo_bar" value="bar" name="foo"/>'
    >>> c = Checkbox('foo', value='bar')
    >>> c.validate('on')
    True
    >>> c.render()
    u'<input type="hidden" name="foo" value="0"><input type="checkbox" id="field-foo_bar" value="bar" name="foo"/>'
    """

    def __init__(self, name, *validators, **attrs):
        self.checked = attrs.pop('checked', False)
        Input.__init__(self, name, *validators, **attrs)

    def get_default_id(self):
        value = safestr(self.value or "")
        return ID_TEMPLATE % self.name + '_' + value.replace(' ', '_')

    def render(self):
        attrs = self.attrs.copy()
        attrs['type'] = 'checkbox'
        attrs['name'] = self.name
        attrs['value'] = self.value

        if self.checked:
            attrs['checked'] = 'checked'
        return '<input type="hidden" name="%s" value="0">' \
               '<input %s/>' % (attrs['name'], attrs)

    def set_value(self, value):
        self.checked = bool(value)

    def get_value(self):
        return self.checked


class MultiCheckbox(InputWithArgs):
    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        x = '<input id="%s" type="hidden" name="%s" value="">' % (ID_TEMPLATE % self.name,
                                                                  self.name)
        x += '<div class="multicheckbox">'
        for value, label in self.args:
            x += self._render_checkbox(value, label)
        x += '</div>'
        return x

    def _render_checkbox(self, value, label):
        attrs = AttributeList({
            'type': 'checkbox',
            'name': self.name,
            'value': value
        })

        if self.value == value or (isinstance(self.value, list) and value in self.value):
            attrs['checked'] = 'checked'
        return '<label><input %s/>%s</label>' % (attrs, label)


class Button(Input):
    """HTML Button.

    >>> Button("save").render()
    u'<button id="field-save" name="save">save</button>'
    >>> Button("action", value="save", html="<b>Save Changes</b>").render()
    u'<button id="field-action" value="save" name="action"><b>Save Changes</b></button>'
    """

    def __init__(self, name, *validators, **attrs):
        super(Button, self).__init__(name, *validators, **attrs)
        self.description = ""

    def render(self):
        attrs = self.attrs.copy()
        attrs['name'] = self.name
        if self.value is not None:
            attrs['value'] = self.value
        html = attrs.pop('html', None) or websafe(self.name)
        return '<button %s>%s</button>' % (attrs, html)


class Hidden(Input):
    """Hidden Input.

        >>> Hidden(name='foo', value='bar').render()
        u'<input type="hidden" id="field-foo" value="bar" name="foo"/>'
    """

    def is_hidden(self):
        return True

    def get_type(self):
        return 'hidden'


class File(Input):
    """File input.

        >>> File(name='f').render()
        u'<input type="file" id="field-f" name="f"/>'
    """

    def get_type(self):
        return 'file'


class HorizontalLine(object):
    def __init__(self, name, *validators, **attrs):
        self.name = name

        self.description = attrs.pop('description', name)
        self.value = attrs.pop('value', None)
        self.pre = attrs.pop('pre', "")
        self.post = attrs.pop('post', "")
        self.note = None
        self.required = attrs.pop('required', False)
        self.attrs = attrs = AttributeList(attrs)

        self.id = attrs.setdefault('id', self.get_default_id())

        if 'class_' in attrs:
            attrs['class'] = attrs['class_']
            del attrs['class_']

    def is_hidden(self):
        return False

    def get_type(self):
        raise NotImplementedError

    def get_default_id(self):
        return "hr-%s" % self.name

    def validate(self, source, field_name=None):
        # Don't need to validate HorizontalLine
        return True

    def set_value(self, value):
        pass

    def get_value(self):
        pass

    def render(self):
        attrs = self.attrs.copy()
        return '<div %s><hr /></div>' % attrs

    def rendernote(self, note):
        return ""

    def addatts(self):
        # add leading space for backward-compatibility
        return " " + str(self.attrs)

    def __str__(self):
        self.render()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
