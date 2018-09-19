#
# Foris - web administration interface for OpenWrt based on NETCONF
# Copyright (C) 2018 CZ.NIC, z.s.p.o. <http://www.nic.cz>
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


WORKFLOW_OLD = "old"
WORKFLOW_MIN = "min"
WORKFLOW_ROUTER = "router"
WORKFLOWS = [
    WORKFLOW_OLD,
    WORKFLOW_MIN,
    WORKFLOW_ROUTER
]


class StandardMessages(object):
    PASSWORD_PASSED_DEFAULT = [
        _(
            "Welcome to Foris web interface. This guide will help you to setup your router. "
            "Firstly it is required to set your password. Note the security of our home "
            "network is in your hands, so try not to use weak passwords."
        ),
        _(
            "Your password seems to be set. You may proceed to the next step."
        ),
    ]
    PASSWORD_CURRENT_DEFAULT = [
        PASSWORD_PASSED_DEFAULT[0],
    ]

    PROFILE_PASSED_DEFAULT = [
        _(
            "Choose one of the possible setup workflows."
        ),
        _(
            "Your profile was set. You may proceed to other step."
        )
    ]
    PROFILE_CURRENT_DEFAULT = [
        PROFILE_PASSED_DEFAULT[0],
    ]

    NETWORKS_PASSED_DEFAULT = [
        _(
            "Here you need to decide which interfaces belongs to which network. "
            "If you are in doubt use the current settings."
        ),
        _(
            "You've configured your network interfaces. "
            "It seems that you didn't break any crucial network settings so you can safely "
            "proceed to the next step."
        ),
    ]
    NETWORKS_CURRENT_DEFAULT = [
        NETWORKS_PASSED_DEFAULT[0],
    ]

    WAN_PASSED_DEFAULT = [
        _(
            "In order to access the internet you need to configure your WAN interface."
        ),
        _(
            "You've configured your wan interface. "
            "Try to run connection test to see whether it is working properly and "
            "if so you can safely proceed to the next step."
        ),
    ]
    WAN_CURRENT_DEFAULT = [
        WAN_PASSED_DEFAULT[0],
    ]

    TIME_PASSED_DEFAULT = [
        _(
            "Now you need to set the time and timezone of your device."
        ),
        _(
            "Your time and timezone seem to be set. Please make sure that the time matches "
            "the time on your computer if not try to update it via ntp or manually."
        ),
    ]
    TIME_CURRENT_DEFAULT = [
        TIME_PASSED_DEFAULT[0],
    ]

    DNS_PASSED_DEFAULT = [
        _(
            "A proper dns resolving is one of the key security features of your router. "
            "Let's configure it now."
        ),
        _(
            "You've updated your dns configuration. "
            "Try to run connection test to see whether your dns resolver is properly set."
        )
    ]
    DNS_CURRENT_DEFAULT = [
        DNS_PASSED_DEFAULT[0],
    ]

    UPDATER_PASSED_DEFAULT = [
        _(
            "Finally you need to set your automatic updates configuration."
        ),
        _(
            "Note that after you update the settings, you'll exit the guide mode and "
            "new items will appear in the menu."
        ),
    ]
    UPDATER_CURRENT_DEFAULT = [
        UPDATER_PASSED_DEFAULT[0],
        UPDATER_PASSED_DEFAULT[1],
    ]

    MSG_MAP_DEFAULT = {
        "passed": {
            "password": PASSWORD_PASSED_DEFAULT,
            "profile": PROFILE_PASSED_DEFAULT,
            "networks": NETWORKS_PASSED_DEFAULT,
            "wan": WAN_PASSED_DEFAULT,
            "time": TIME_PASSED_DEFAULT,
            "dns": DNS_PASSED_DEFAULT,
            "updater": UPDATER_PASSED_DEFAULT,
        },
        "current": {
            "password": PASSWORD_CURRENT_DEFAULT,
            "profile": PROFILE_CURRENT_DEFAULT,
            "networks": NETWORKS_CURRENT_DEFAULT,
            "wan": WAN_CURRENT_DEFAULT,
            "time": TIME_CURRENT_DEFAULT,
            "dns": DNS_CURRENT_DEFAULT,
            "updater": UPDATER_CURRENT_DEFAULT,
        }
    }

    # to customize texts per workflow (e.g. instructions to replug cable)
    MSG_MAP_WORKFLOWS = {
        "old": MSG_MAP_DEFAULT,
    }

    @staticmethod
    def get(step, current, workflow):
        workflow_messages = StandardMessages.MSG_MAP_WORKFLOWS.get(
            workflow, StandardMessages.MSG_MAP_DEFAULT)

        state = "current" if current else "passed"
        messages = workflow_messages.get(state, StandardMessages.MSG_MAP_DEFAULT[state])
        return messages.get(step, StandardMessages.MSG_MAP_DEFAULT[state][step])


class Guide(object):

    def __init__(self, backend_data):
        self.enabled = backend_data["enabled"]
        self.workflow = backend_data["workflow"]
        self.passed = backend_data["passed"]
        self.steps = backend_data["workflow_steps"]
        self.current = backend_data.get("next_step", None)

    @property
    def available_tabs(self):
        return self.passed + ([self.current] if self.current else [])

    def is_available(self, step):
        if not self.enabled:
            return True
        return step in self.available_tabs

    def message(self, step=None):
        if not self.enabled:
            return None
        step = step or self.current
        return StandardMessages.get(step, step == self.current, self.workflow)

    def is_guide_step(self, step):
        return step in self.steps


class Workflow(object):
    TITLES = {
        WORKFLOW_OLD: "Workflow for older routers",
        WORKFLOW_MIN: "Minimal workflow",
        WORKFLOW_ROUTER: "Router workflow",
    }
    DESCRIPTIONS = {
        WORKFLOW_OLD: _("Workflow for older routers and older turris OS versions (before 4.0)."),
        WORKFLOW_MIN: _(
            "Just set your password and you are ready to go. "
            "This workflow is aimed to more advanced users who intend not to use the web gui. "
            "It acturally exits the guide after you choose this workflow."
        ),
        WORKFLOW_ROUTER: _(
            "After you finish this workflow your device will be able to act as a fully "
            "functional router. It assumes that you want to have more or less standard "
            "network setup."
        ),
    }

    def __init__(self, workflow, current, recommended):
        """ Create object which describes a guide workflow

        :type current: bool
        :type recommended: bool

        """
        if workflow not in WORKFLOWS:
            raise KeyError("Workflow '%s' was not found." % workflow)

        self.name = workflow
        self.title = Workflow.TITLES[workflow]
        self.description = Workflow.DESCRIPTIONS[workflow]
        self.current = current
        self.recommended = recommended

    @property
    def img(self):
        return "img/workflow-%s.svg" % self.name
