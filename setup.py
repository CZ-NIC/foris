from distutils.core import setup
import os
import re
import subprocess

import foris


def update_version_file(version_file_path, version_number):
    """Read file containing version variable and update it to version_number."""
    with open(version_file_path, "r") as f:
        content = f.readlines()
    with open(version_file_path, "w") as f:
        version_re = re.compile(r'^__version__ = "[^"]*"')
        for line in content:
            f.write(version_re.sub('__version__ = "%s"' % version_number, line))


def get_version(update_file=True):
    """Get version from Git tags, optionally save it to foris module."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isdir(os.path.join(base_dir, ".git")):
        if foris.__version__ != "unknown":
            # fallback to stored version (e.g. when making package)
            return foris.__version__
        return "unknown"
    p = subprocess.Popen(["git", "describe", "--tags", "--dirty"], stdout=subprocess.PIPE)
    stdout = p.communicate()[0].strip()
    # correct tags with version must start with "package-v"
    assert stdout.startswith("package-v")
    version_number = stdout[len("package-v"):]
    if update_file:
        init_file = os.path.join(base_dir, "foris", "__init__.py")
        update_version_file(init_file, version_number)
    return version_number


setup(
    name="Foris",
    version=get_version(),
    description="Web administration interface for OpenWrt based on NETCONF",
    author="CZ.NIC, z. s. p. o.",
    author_email="stepan.henek@nic.cz",
    url="https://gitlab.labs.nic.cz/turris/foris/",
    license="GPL-3.0",
    requires=[
        "bottle",
        "bottle_i18n",
        "ncclient",
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
        "foris.wizard",
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
            "static/img/wizard/*",
            "static/js/*.min.js",
            "static/js/contrib/*",
            "utils/*.pickle2",
        ]
    },
)
