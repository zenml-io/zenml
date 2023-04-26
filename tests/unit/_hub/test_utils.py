#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Unit tests for zenml._hub.utils.py"""

import pytest

from zenml._hub.utils import parse_plugin_name, plugin_display_name


@pytest.mark.parametrize(
    "plugin_name, author, name, version",
    [
        ("author/plugin_name:version", "author", "plugin_name", "version"),
        ("author/plugin_name", "author", "plugin_name", "latest"),
        ("plugin_name:version", None, "plugin_name", "version"),
        ("plugin_name", None, "plugin_name", "latest"),
    ],
)
def test_parse_plugin_name(plugin_name, author, name, version):
    """Unit test for `parse_plugin_name`."""
    assert parse_plugin_name(plugin_name) == (author, name, version)

    # Test with different separators.
    plugin_name_2 = name
    if author:
        plugin_name_2 = f"{author},{plugin_name_2}"
    if version:
        plugin_name_2 = f"{plugin_name_2};{version}"
    author_2, name_2, version_2 = parse_plugin_name(
        plugin_name_2,
        author_separator=",",
        version_separator=";",
    )
    print(plugin_name, plugin_name_2)
    print(author, author_2)
    print(name, name_2)
    print(version, version_2)
    assert author_2 == author
    assert name_2 == name
    assert version_2 == version


@pytest.mark.parametrize(
    "invalid_plugin_name",
    [
        "",
        "invalid/plugin/name",
        "invalid:plugin:name",
    ],
)
def test_parse_invalid_plugin_name(invalid_plugin_name):
    """Unit test for `parse_plugin_name`."""
    with pytest.raises(ValueError):
        parse_plugin_name(invalid_plugin_name)


@pytest.mark.parametrize(
    "plugin_name, author, name, version",
    [
        ("author/plugin_name:version", "author", "plugin_name", "version"),
        ("author/plugin_name:latest", "author", "plugin_name", None),
        ("plugin_name:version", None, "plugin_name", "version"),
        ("plugin_name:latest", None, "plugin_name", None),
    ],
)
def test_plugin_display_name(plugin_name, author, name, version):
    """Unit test for `plugin_display_name`."""
    assert plugin_display_name(name, version, author) == plugin_name
