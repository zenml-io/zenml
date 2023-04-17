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
"""Test zenml hub CLI commands."""

from click.testing import CliRunner

from zenml._hub.constants import ZENML_HUB_ADMIN_USERNAME
from zenml.cli.cli import cli
from zenml.cli.hub import _is_plugin_installed

EXAMPLE_PLUGIN_NAME = "langchain_qa_example"


def test_hub_list():
    """Test that zenml hub list does not fail."""
    runner = CliRunner()
    list_command = cli.commands["hub"].commands["list"]
    result = runner.invoke(list_command)
    assert result.exit_code == 0


def test_hub_install_uninstall():
    """Test installing and uninstalling a plugin."""
    runner = CliRunner()
    install_command = cli.commands["hub"].commands["install"]
    result = runner.invoke(install_command, [EXAMPLE_PLUGIN_NAME, "-y"])
    assert result.exit_code == 0
    assert _is_plugin_installed(
        author=ZENML_HUB_ADMIN_USERNAME, plugin_name=EXAMPLE_PLUGIN_NAME
    )

    uninstall_command = cli.commands["hub"].commands["uninstall"]
    result = runner.invoke(uninstall_command, [EXAMPLE_PLUGIN_NAME])
    assert result.exit_code == 0
    assert not _is_plugin_installed(
        author=ZENML_HUB_ADMIN_USERNAME, plugin_name=EXAMPLE_PLUGIN_NAME
    )
