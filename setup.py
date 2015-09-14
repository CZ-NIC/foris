from distutils.core import setup

from foris import __version__

setup(
    name="Foris",
    version=__version__,
    description="Web administration interface for OpenWrt based on NETCONF",
    author="CZ.NIC, z. s. p. o.",
    author_email="jan.cermak@nic.cz",
    url="https://gitlab.labs.nic.cz/turris/foris/",
    license="LICENSE",
    requires=[
        "beaker",
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
        "foris.nuci",
        "foris.nuci.modules",
        "foris.utils",
    ],
    package_data={
        '': [
            "locale/**/LC_MESSAGES/*.mo",
            "templates/**",
            "templates/**/*",
            "static/css/*.css",
            "static/img/*",
            "static/img/wizard/*",
            "static/js/*.min.js",
            "static/js/contrib/*",
        ]
    },
)
