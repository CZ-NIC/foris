#
# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2017 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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


from foris.utils.translators import _


class StandardMessages(object):
    MESSAGES_CURRENT_MAP = {
        "password": [
            _(
                "Welcome to Foris configuration. Bla bla bla"
            ),
        ],
        "wan": [
            _(
                "In order to access the internet you need to configure your WAN device. Bla bla bla"
            ),
        ],
        "time": [
            _("In order to verify TLS certificates validity your time has to be properly set. ..."),
        ],
        "dns": [
            _("To resolve ip addresses to hostnames ..."),
        ],
    }

    MESSAGES_MAP = {
        "password": [
            MESSAGES_CURRENT_MAP["password"][0],
            _("Your password seems to be set. You may proceed to the next step"),
        ],
        "wan": [
            MESSAGES_CURRENT_MAP["wan"][0],
            _(
                "You've configured your wan interface. "
                "Try to run connection test to see whether it is working properly"
            ),
        ],
        "time": [
            MESSAGES_CURRENT_MAP["time"][0],
            _(
                "Your timezone seems to be set. Please make sure that the time is correct "
                " because bla bla bla"
            )
        ],
        "dns": [
            MESSAGES_CURRENT_MAP["dns"][0],
            _(
                "You've updated your dns configuration. "
                "Try to run connection test to see whether your dns is properly set."
            ),
        ],
        "updater": [
            _("To keep your software up-to-date you need to configure updater first."),
        ],
    }

    @staticmethod
    def get(step, current):
        if current and step in StandardMessages.MESSAGES_CURRENT_MAP:
            return StandardMessages.MESSAGES_CURRENT_MAP[step]
        return StandardMessages.MESSAGES_MAP[step]


class Guide(object):
    WORKFLOW_STANDARD = "standard"

    STEP_PASSWORD = "password"
    STEP_WAN = "wan"
    STEP_TIME = "time"
    STEP_DNS = "dns"
    STEP_UPDATER = "updater"

    STANDARD_STEPS = (
        STEP_PASSWORD,
        STEP_WAN,
        STEP_TIME,
        STEP_DNS,
        STEP_UPDATER,
    )

    def __init__(self, backend_data):
        self.enabled = backend_data["enabled"]
        self.workflow = backend_data["workflow"]
        self.current = self._get_current(backend_data["passed"])

        if not self.current:  # All required steps are passed -> disable guide
            self.enabled = False

    def _get_current(self, passed):
        if self.workflow == Guide.WORKFLOW_STANDARD:
            for step in Guide.STANDARD_STEPS:
                if step not in passed:
                    return step
            return None

        raise NotImplementedError("unknown workflow %s" % self.workflow)

    @property
    def available_tabs(self):
        if self.workflow == Guide.WORKFLOW_STANDARD:
            return Guide.STANDARD_STEPS[:Guide.STANDARD_STEPS.index(self.current) + 1]

        raise NotImplementedError("unknown workflow %s" % self.workflow)

    def is_available(self, step):
        if not self.enabled:
            return True
        return step in self.available_tabs

    def message(self, step=None):
        if not self.enabled:
            return None
        if self.workflow == Guide.WORKFLOW_STANDARD:
            step = step if step else self.current
            return StandardMessages.get(step, step == self.current)

        raise NotImplementedError("unknown workflow %s" % self.workflow)
