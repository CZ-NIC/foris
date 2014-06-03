#!/bin/sh

green () { echo -e "\033[32m$1\033[0m"; }
yellow () { echo -e "\033[33m$1\033[0m"; }
require_python_module () {
    # syntax: required_python_module verbose_name module_name
    if `python -c "import $2" > /dev/null 2>&1`; then
        green "$1 module found."
    else
        yellow "Installing $1 module."
        easy_install $1
    fi
}

if [ ! -x `which easy_install` ]; then
    yellow "Installing easy_install."
    curl -k https://bootstrap.pypa.io/ez_setup.py | python - --insecure
else
    green "Found easy_install."
fi

require_python_module Webtest webtest
require_python_module nose nose
require_python_module coverage coverage