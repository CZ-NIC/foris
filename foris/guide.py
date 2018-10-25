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
WORKFLOW_BRIDGE = "bridge"
WORKFLOW_UNSET = "unset"
WORKFLOWS = [
    WORKFLOW_UNSET,
    WORKFLOW_OLD,
    WORKFLOW_MIN,
    WORKFLOW_ROUTER,
    WORKFLOW_BRIDGE,
]


class MessagesDefault():
    PASSWORD_PASSED = [
        _(
            "Welcome to Foris web interface. This guide will help you to setup your router. "
            "Firstly it is required to set your password. Note the security of your home "
            "network is in your hands, so try not to use weak passwords."
        ),
        _(
            "Your password seems to be set. You may proceed to the next step."
        ),
    ]
    PASSWORD_CURRENT = [
        PASSWORD_PASSED[0],
    ]

    PROFILE_PASSED = [
        _(
            "Choose one of the possible setup workflows."
        ),
        _(
            "The workflow was set. You may proceed to next step."
        )
    ]
    PROFILE_CURRENT = [
        PROFILE_PASSED[0],
    ]

    NETWORKS_PASSED = [
        _(
            "Here you need to decide which interfaces belongs to which network."
        ),
        _(
            "If you are in doubt use the current settings."
        ),
        _(
            "You've configured your network interfaces. "
            "It seems that you didn't break any crucial network settings so you can safely "
            "proceed to the next step."
        ),
    ]
    NETWORKS_CURRENT = [
        NETWORKS_PASSED[0],
    ]

    WAN_PASSED = [
        _(
            "In order to access the internet you need to configure your WAN interface."
        ),
        _(
            "You've configured your WAN interface. "
            "Try to run connection test to see whether it is working properly and "
            "if so you can safely proceed to the next step."
        ),
    ]
    WAN_CURRENT = [
        WAN_PASSED[0],
    ]

    LAN_PASSED = [
        _(
            "Now you should configure your LAN interface. Note that when you change your network "
            "settings you probably won't be able to connect to the configuration interface "
            "unless you restart the network on your current device."
        ),
        _(
            "You've configured your LAN interface. "
            "Try to test whether settings work properly and if so "
            "you can safely proceed to the next step."
        ),
    ]
    LAN_CURRENT = [
        LAN_PASSED[0],
    ]

    TIME_PASSED = [
        _(
            "Now you need to set the time and timezone of your device."
        ),
        _(
            "Your time and timezone seem to be set. Please make sure that the time matches "
            "the time on your computer if not try to update it via ntp or manually."
        ),
    ]
    TIME_CURRENT = [
        TIME_PASSED[0],
    ]

    DNS_PASSED = [
        _(
            "A proper DNS resolving is one of the key security features of your router. "
            "Let's configure it now."
        ),
        _(
            "You've updated your DNS configuration. "
            "Try to run connection test to see whether your DNS resolver is properly set."
        )
    ]
    DNS_CURRENT = [
        DNS_PASSED[0],
    ]

    UPDATER_PASSED = [
        _(
            "Now you need to configure automatic updates ouf your device."
        ),
        _(
            "Please wait till the updater finishes its run."
        ),
    ]
    UPDATER_CURRENT = [
        UPDATER_PASSED[0]
    ]

    FINISHED_PASSED = [
        _("You have sucessfully configured your device.")
    ]
    FINISHED_CURRENT = FINISHED_PASSED

    @classmethod
    def get(cls, step, current):
        state = "CURRENT" if current else "PASSED"
        return getattr(cls, "%s_%s" % (step.upper(), state))


class MessageBridge(MessagesDefault):
    NETWORKS_PASSED = [
        MessagesDefault.NETWORKS_PASSED[0],
        _(
            "You chose to act as local server this means that it doesn't make sense to put "
            "any interfaces to your WAN and Guest Network. So it is a good idea to assign all "
            "iterfaces to LAN."
        ),
        MessagesDefault.NETWORKS_PASSED[2],
    ]
    NETWORKS_CURRENT = [
        NETWORKS_PASSED[0],
        NETWORKS_PASSED[1],
    ]

    LAN_PASSED = [
        _(
            "To act as a local server, there's no need to manage LAN "
            "(if you still want to manage it reset the guide and choose the Router workflow). "
            "You probably want to act as a client here thus select "
            "<strong>Unmanaged</strong> mode here. "
        ),
        _(
            "If you select the <strong>static</strong> configuration be sure that the IP "
            "addresses are entered correctly otherwise you won't be able to access this "
            "configuration iterface when the new settings are applied."
        ),
        _(
            "If you select the <strong>DHCP</strong> method you probably you need to obtain "
            "a new IP address of this device. You can obtain it from the DHCP server which "
            "is managing your LAN. Then you need to connect to the new IP "
            "address to proceed the guide."
        ),
        _(
            "Note that either way you might need to re-plug your ethernet cabels after you update "
            "the settings here."
        ),
        _(
            "Please test whether the settings you provided are correctly working. "
            "This means that you can access the configuration interface of your device "
            "and your device is able to access the internet "
            "(you can use the connection test below)."
        )
    ]
    LAN_CURRENT = [
        LAN_PASSED[0],
        LAN_PASSED[1],
        LAN_PASSED[2],
        LAN_PASSED[3],
    ]

    FINISHED_PASSED = [
        _(
            "The device setup is finished. Now your device should be able to act as a server "
            "on your local network."
        )
    ]
    FINISHED_CURRENT = FINISHED_PASSED


class MessageMin(MessagesDefault):
    FINISHED_PASSED = [
        _(
            "Minimal device setup is finished. Note that you probably need to perform some "
            "further configuration updates to fit the device to your needs."
        )
    ]
    FINISHED_CURRENT = FINISHED_PASSED


class MessageRouter(MessagesDefault):
    FINISHED_PASSED = [
        _(
            "The device setup is finished. Now your device is able to act as a router and route "
            "network traffic among LAN, WAN and guest network."
        )
    ]
    FINISHED_CURRENT = FINISHED_PASSED


def get_guide_messages(step, current, workflow):
    WORKFLOW_MAP = {
        WORKFLOW_BRIDGE: MessageBridge,
        WORKFLOW_MIN: MessageMin,
        WORKFLOW_ROUTER: MessageRouter,
    }
    return WORKFLOW_MAP.get(workflow, MessagesDefault).get(step, current)


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

    def message(self, step):
        if not self.enabled:
            return None
        step = step or self.current
        return get_guide_messages(step, step == self.current, self.workflow)

    def is_guide_step(self, step):
        return step in self.steps

    def display_leave_guide(self, last):
        if last:
            return self.current != "finished"
        else:
            return True


class Workflow(object):
    TITLES = {
        WORKFLOW_OLD: _("Old"),
        WORKFLOW_MIN: _("Minimal"),
        WORKFLOW_ROUTER: _("Router"),
        WORKFLOW_BRIDGE: _("Local Server"),
        WORKFLOW_UNSET: _("Unset"),
    }
    DESCRIPTIONS = {
        WORKFLOW_UNSET: _("The workflow wasn't set yet."),
        WORKFLOW_OLD: _("Workflow for older routers and older turris OS versions (before 4.0)."),
        WORKFLOW_MIN: _(
            "Just set your password and you are ready to go. "
            "This workflow is aimed to more advanced users who intend not to use the web gui. "
        ),
        WORKFLOW_ROUTER: _(
            "After you finish this workflow your device will be able to act as a fully "
            "functional router. It assumes that you want to have more or less standard "
            "network setup."
        ),
        WORKFLOW_BRIDGE: _(
            "This workflow will help you to setup your device to act as a local server. "
            "It means that the device will provide some kind of service to other devices "
            "within your local network (e.g. act as a network attached storage)."
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
