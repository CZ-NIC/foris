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


from foris.config_handlers import misc
from foris.state import current_state
from foris.utils import messages
from foris.utils.translators import _

from .base import ConfigPageMixin


class PasswordConfigPage(ConfigPageMixin, misc.PasswordHandler):
    slug = "password"
    menu_order = 10
    template = "config/password"
    template_type = "jinja2"

    def __init__(self, *args, **kwargs):
        super(PasswordConfigPage, self).__init__(change=current_state.password_set, *args, **kwargs)

    def save(self, *args, **kwargs):
        result = super(PasswordConfigPage, self).save(no_messages=True, *args, **kwargs)
        wrong_old_password = self.form.callback_results.get('wrong_old_password', False)
        system_password_no_error = self.form.callback_results.get('system_password_no_error', None)
        foris_password_no_error = self.form.callback_results.get('foris_password_no_error', None)

        compromised = self.form.callback_results.get("compromised")
        if compromised:
            messages.error(
                _(
                    "The password you've entered has been compromised. "
                    "It appears %(count)d times in '%(list)s' list."
                ) % dict(count=compromised['count'], list=compromised['list'])
            )
            return result

        if wrong_old_password:
            messages.error(_("Old password you entered was not valid."))
            return result

        if system_password_no_error is not None:
            if system_password_no_error:
                messages.success(_("System password was successfully saved."))
            else:
                messages.error(_("Failed to save system password."))
        if foris_password_no_error is not None:
            if foris_password_no_error:
                messages.success(_("Foris password was successfully saved."))
            else:
                messages.error(_("Failed to save Foris password."))

        return result
