#
# Foris
# Copyright (C) 2019 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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

import bottle
import typing

from bottle import template

from foris import fapi
from foris.state import current_state
from foris.utils import messages
from foris.utils.translators import _


class BaseConfigPage(object):
    no_url = False
    menu_order = 50
    slug: typing.Optional[str] = None
    userfriendly_title: typing.Optional[str]
    menu_title: typing.Optional[str] = None
    subpages: typing.Iterable[typing.Type["ConfigPageMixin"]] = []

    @staticmethod
    def get_menu_tag_static(cls):
        if current_state.guide.enabled and current_state.guide.current == cls.slug:
            return {"show": True, "hint": "", "text": "<i class='fas fa-reply'></i>"}
        else:
            return {"show": False, "hint": "", "text": ""}

    @classmethod
    def get_menu_tag(cls):
        return ConfigPageMixin.get_menu_tag_static(cls)

    @staticmethod
    def is_visible_static(cls):
        if current_state.guide.enabled:
            return cls.slug in current_state.guide.steps

        return True

    @classmethod
    def is_visible(cls):
        return ConfigPageMixin.is_visible_static(cls)

    @staticmethod
    def is_enabled_static(cls):
        if current_state.guide.enabled:
            return cls.slug in current_state.guide.available_tabs

        return True

    @classmethod
    def is_enabled(cls):
        return ConfigPageMixin.is_enabled_static(cls)

    @classmethod
    def subpage_slugs(cls):
        return [e.slug for e in cls.subpages]


class ConfigPageMixin(BaseConfigPage):
    # page url part /config/<slug>
    template = "config/main"
    template_type = "simple"

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

    def get_page_form(
        self, form_name: str, data: dict, controller_id: str
    ) -> typing.Tuple[fapi.ForisAjaxForm, typing.Callable[[dict], typing.Tuple["str", "str"]]]:
        """Returns appropriate foris form and handler to generate response
        """
        raise bottle.HTTPError(404, "No forms specified for this page.")

    def call_insecure(self, identifier):
        """Handels insecure request (no login required)

        :param namespace: namespace of the storage (e.g. tokens)
        :return: object that can be passed as HTTP response to Bottle
        """
        raise bottle.HTTPError(404, "No storage specified for this page.")

    def default_template(self, **kwargs):
        if self.template_type == "jinja2":
            page_template = "%s.html.j2" % self.template
            kwargs["template_adapter"] = bottle.Jinja2Template
        else:
            page_template = self.template
        return template(
            page_template, title=_(kwargs.pop("title", self.userfriendly_title)), **kwargs
        )

    def render(self, **kwargs):
        try:
            form = getattr(self, "form")
            first_section = form.sections[0]
            title = first_section.title
            description = first_section.description
        except (NotImplementedError, AttributeError):
            form = None
            title = self.userfriendly_title
            description = None

        return self.default_template(form=form, title=title, description=description, **kwargs)

    def save(self, *args, **kwargs):
        no_messages = kwargs.pop("no_messages", False)
        result = super(ConfigPageMixin, self).save(*args, **kwargs)
        if no_messages:
            return result
        if result:
            messages.success(_("Configuration was successfully saved."))
        else:
            messages.warning(_("There were some errors in your input."))
        return result


class JoinedPages(BaseConfigPage):
    userfriendly_title = None
    no_url = True
