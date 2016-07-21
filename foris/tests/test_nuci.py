from xml.etree import cElementTree as ET

import pytest

from foris.nuci.modules.uci_raw import (
    Uci,
    Config,
    Section,
    Option,
    build_option_uci_tree,
)


def test_build_option_uci_tree_correct_xml():
    uci = Uci()
    updater = Config("updater")
    uci.add(updater)
    override = Section("override", "override")
    updater.add(override)
    override.add(Option("disable", True))

    built_tree = build_option_uci_tree("updater.override.disable", "override", True)

    assert ET.tostring(built_tree.get_xml()) == ET.tostring(uci.get_xml())


def test_build_option_uci_tree_invalid_path():
    with pytest.raises(ValueError):
        build_option_uci_tree("updater.override.a.a", "override", "1")

    with pytest.raises(ValueError):
        build_option_uci_tree("updater.override", "override", "1")


def test_build_option_uci_tree_anonymous_section():
    with pytest.raises(ValueError):
        build_option_uci_tree("firewall.@rule[1].name", "rule", "a")


def test_option_bool_serialization():
    option_bool = Option("test", True)
    option_str = Option("test", "1")
    assert option_bool.value == option_str.value == "1"

    option_bool = Option("test", False)
    option_str = Option("test", "0")
    assert option_bool.value == option_str.value == "0"
