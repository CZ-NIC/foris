#!/usr/bin/env python

import os

from setuptools import setup
from setuptools.command.build_py import build_py

from foris import __version__


class BuildCmd(build_py):
    def run(self):
        # compile translation
        from babel.messages import frontend as babel
        cmd = babel.compile_catalog()
        cmd.initialize_options()
        cmd.directory = os.path.join(os.path.dirname(__file__), "foris", "locale")
        cmd.finalize_options()
        cmd.run()

        # run original build cmd
        build_py.run(self)


setup(
    name="Foris",
    version=__version__,
    description="Web administration interface for OpenWrt based on NETCONF",
    author="CZ.NIC, z. s. p. o.",
    author_email="stepan.henek@nic.cz",
    url="https://gitlab.labs.nic.cz/turris/foris/",
    license="GPL-3.0",
    requires=[
        "bottle",
        "bottle_i18n",
    ],
    setup_requires=[
        'babel',
    ],
    provides=[
        "foris"
    ],
    packages=[
        "foris",
        "foris.config_handlers",
        "foris.config",
        "foris.common",
        "foris.langs",
        "foris.plugins",
        "foris.utils",
        "foris.ubus",
        "foris.middleware",
    ],
    package_data={
        '': [
            "LICENSE",
            "locale/**/LC_MESSAGES/*.mo",
            "templates/**",
            "templates/**/*",
            "static/css/*.css",
            "static/fonts/*",
            "static/img/*",
            "static/js/*.js",
            "static/js/contrib/*",
            "utils/*.pickle2",
        ]
    },
    cmdclass={
        "build_py": BuildCmd,
    }
)
