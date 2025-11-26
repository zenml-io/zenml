#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

import importlib
import os

import click
import pytest
from click.testing import CliRunner

from zenml.cli.cli import ZenMLCLI, cli
from zenml.cli.formatter import ZenFormatter
from zenml.enums import StoreType
from zenml.exceptions import IllegalOperationError


@pytest.fixture(scope="function")
def runner(request):
    return CliRunner()


def test_cli_command_defines_a_cli_group() -> None:
    """Check that cli command defines a CLI group when invoked."""
    assert isinstance(cli, ZenMLCLI)


def test_cli(runner):
    """Check that basic cli call works."""
    result = runner.invoke(cli)
    assert not result.exception
    assert result.exit_code == 0


def test_ZenMLCLI_formatter():
    """
    Test the ZenFormatter class.
    """
    zencli = ZenMLCLI()
    context = click.Context(zencli)
    formatter = ZenFormatter(context)
    assert isinstance(formatter, ZenFormatter)


def test_cli_sets_custom_source_root_if_outside_of_repository(
    clean_client, mocker
):
    """Tests that the CLI root group sets a custom source root if outside of a
    ZenML repository."""
    mock_set_custom_source_root = mocker.patch(
        "zenml.utils.source_utils.set_custom_source_root"
    )
    runner = CliRunner()

    # Invoke a subcommand so the root CLI group gets called
    runner.invoke(cli, ["version"])

    mock_set_custom_source_root.assert_called_with(source_root=os.getcwd())


def test_cli_does_not_set_custom_source_root_if_inside_repository(
    clean_project, mocker
):
    """Tests that the CLI root group does **NOT** set a custom source root if
    inside of a ZenML repository."""
    mock_set_custom_source_root = mocker.patch(
        "zenml.utils.source_utils.set_custom_source_root"
    )
    runner = CliRunner()

    # Invoke a subcommand so the root CLI group gets called
    runner.invoke(cli, ["version"])

    mock_set_custom_source_root.assert_not_called()


def _mock_rest_store_environment(mocker):
    """Mock dependencies needed for connect_to_server REST flow."""
    credentials_store = mocker.Mock()
    credentials_store.has_valid_credentials.return_value = True
    mocker.patch(
        "zenml.cli.login.get_credentials_store", return_value=credentials_store
    )
    mocker.patch(
        "zenml.cli.login.BaseZenStore.get_store_type",
        return_value=StoreType.REST,
    )
    mocker.patch(
        "zenml.cli.login.RestZenStoreConfiguration", return_value="rest-config"
    )
    mocker.patch("zenml.cli.login.cli_utils.declare")
    mocker.patch("zenml.cli.login.web_login")


def test_connect_to_server_sets_project_after_success(mocker):
    """Project flag should set the active project after connecting."""
    _mock_rest_store_environment(mocker)
    login_module = importlib.import_module("zenml.cli.login")
    mock_gc = mocker.patch("zenml.cli.login.GlobalConfiguration")
    mock_gc.return_value.set_store.return_value = None
    mock_set_project = mocker.patch("zenml.cli.login._set_active_project")

    login_module.connect_to_server(
        url="https://example.com",
        project="project-67",
    )

    mock_set_project.assert_called_once_with("project-67")


def test_connect_to_server_does_not_set_project_on_failure(mocker):
    """Project change should be skipped if connecting to the store fails."""
    _mock_rest_store_environment(mocker)
    login_module = importlib.import_module("zenml.cli.login")
    mock_gc = mocker.patch("zenml.cli.login.GlobalConfiguration")
    mock_gc.return_value.set_store.side_effect = IllegalOperationError("boom")
    mock_set_project = mocker.patch("zenml.cli.login._set_active_project")
    mocker.patch(
        "zenml.cli.login.cli_utils.error", side_effect=RuntimeError("exit")
    )

    with pytest.raises(RuntimeError):
        login_module.connect_to_server(
            url="https://example.com",
            project="project-67",
        )

    mock_set_project.assert_not_called()
