#!/usr/bin/env python

import os
import glob
import re
import copy

from setuptools import setup
from setuptools.command.build_py import build_py

from foris import __version__


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def merge_po_files():
    from babel.messages.pofile import read_po, write_po

    trans_dirs = glob.glob(os.path.join(BASE_DIR, "foris/locale/*/LC_MESSAGES/"))

    # iterate through translations
    for trans_dir in trans_dirs:
        locale = re.match(r".*\/([a-zA-Z_]+)\/LC_MESSAGES/", trans_dir).group(1)
        foris_path = os.path.join(trans_dir, "foris.po")
        if not os.path.exists(foris_path):
            continue

        # read foris translations
        with open(foris_path, "rb") as f:
            foris_catalog = read_po(f, locale=locale, domain="messages")

        # read tzinfo translations
        tzinfo_path = os.path.join(trans_dir, "tzinfo.po")
        if os.path.exists(tzinfo_path):
            with open(tzinfo_path, "rb") as f:
                tzinfo_catalog = read_po(f, locale=locale, domain="messages")
            for msg in tzinfo_catalog:
                # foris messages will be preffered
                if msg.id not in foris_catalog:
                    # append to foris messages
                    foris_catalog[msg.id] = msg

        # write merged catalogs
        target_path = os.path.join(trans_dir, "messages.po")
        with open(target_path, "wb") as f:
            write_po(f, foris_catalog, no_location=True)


class BuildCmd(build_py):
    def run(self):
        # prepare messages.po
        merge_po_files()

        # compile translation
        from babel.messages import frontend as babel

        distribution = copy.copy(self.distribution)
        cmd = babel.compile_catalog(distribution)
        cmd.directory = os.path.join(os.path.dirname(__file__), "foris", "locale")
        cmd.domain = "messages"
        cmd.ensure_finalized()
        cmd.run()

        # run original build cmd
        build_py.run(self)


setup(
    name="Foris",
    version=__version__,
    description="Web administration interface for OpenWrt based on NETCONF",
    author="CZ.NIC, z. s. p. o.",
    author_email="packaging@turris.cz",
    url="https://gitlab.nic.cz/turris/foris/foris/",
    license="GPL-3.0",
    install_requires=[
        "jinja2",
        "bottle",
        "bottle_i18n",
        "pbkdf2",
        "flup",
        "ubus @ git+https://gitlab.nic.cz/turris/python-ubus.git",
        "paho-mqtt",
    ],
    setup_requires=["babel", "jinja2"],
    provides=["foris"],
    extras_require={"sentry": ["sentry-sdk>=0.7.9"]},
    packages=[
        "foris",
        "foris.config_handlers",
        "foris.config",
        "foris.config.pages",
        "foris.common",
        "foris.langs",
        "foris.plugins",
        "foris.utils",
        "foris.ubus",
        "foris.middleware",
        "foris_plugins",
    ],
    package_data={
        "": [
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
    namespace_packages=["foris_plugins"],
    cmdclass={"build_py": BuildCmd},
    entry_points={"console_scripts": ["foris = foris.__main__:main"]},
)
