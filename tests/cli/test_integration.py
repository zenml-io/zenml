#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import os

import pytest
from click.testing import CliRunner
from zenml.integrations.registry import integration_registry

from zenml.cli.integration import (
    integration,
    install_package,
    uninstall_package
)

NOT_AN_INTEGRATIONS = ["zenflow", "Anti-Tensorflow", "123"]


def test_integration_list() -> None:
    """Test that integration list works as expected and lists all
    integrations"""
    runner = CliRunner()

    result = runner.invoke(integration, ["list"])
    assert result.exit_code == 0
    for implemented_integration in integration_registry.integrations:
        assert implemented_integration in result.output


@pytest.mark.parametrize("not_an_integration", NOT_AN_INTEGRATIONS)
def test_integration_get_requirements_inexistent_integration(
        not_an_integration: str,
) -> None:
    """Tests that the get-requirements sub-command works as expected"""
    runner = CliRunner()

    result = runner.invoke(
        integration,
        ["get-requirements", not_an_integration]
    )
    assert result.exit_code == 1


def test_integration_get_requirements_specific_integration() -> None:
    """Tests that the get-requirements sub-command works as expected"""
    runner = CliRunner()

    result = runner.invoke(integration, ["get-requirements", "airflow"])
    assert result.exit_code == 0


def test_integration_get_requirements_all() -> None:
    """Tests that the get-requirements sub-command works as expected"""
    runner = CliRunner()

    result = runner.invoke(integration, ["get-requirements"])
    assert result.exit_code == 0


@pytest.mark.parametrize("not_an_integration", NOT_AN_INTEGRATIONS)
def test_integration_install_inexistent_integration(
        not_an_integration: str,
) -> None:
    """Tests that the install command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be installed"""
    runner = CliRunner()

    result = runner.invoke(integration, ["install", not_an_integration])
    assert result.exit_code == 1


# TODO[HIGH] mock the install_package and uninstall_package functions
@pytest.mark.skip(reason="During testing no changes should be made to the"
                         "environment. The subprocess running pip install"
                         "should be mocked away")
def test_integration_install_specific_integration() -> None:
    """Tests that the install command behaves as expected when supplied with
    a specific integration"""
    runner = CliRunner()

    result = runner.invoke(integration, ["install", "airflow"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="During testing no changes should be made to the"
                         "environment. The subprocess running pip install"
                         "should be mocked away")
def test_integration_install_all() -> None:
    """Tests that the install command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be installed"""
    runner = CliRunner()

    result = runner.invoke(integration, ["install"])
    assert result.exit_code == 0


@pytest.mark.parametrize("not_an_integration", NOT_AN_INTEGRATIONS)
def test_integration_uninstall_inexistent_integration(
        not_an_integration: str,
) -> None:
    """Tests that the install command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be installed"""
    runner = CliRunner()

    result = runner.invoke(integration, ["uninstall", not_an_integration])
    assert result.exit_code == 1


@pytest.mark.skip(reason="During testing no changes should be made to the"
                         "environment. The subprocess running pip uninstall"
                         "should be mocked away")
def test_integration_uninstall_specific_integration(mocker) -> None:
    """Tests that the uninstall command behaves as expected when supplied with
    a specific integration"""
    runner = CliRunner()
    mocker.patch('tests.cli.test_integration.uninstall_package',
                 return_value=None)
    result = runner.invoke(integration, ["uninstall", "airflow"])
    assert result.exit_code == 0


@pytest.mark.skip(reason="During testing no changes should be made to the"
                         "environment. The subprocess running pip uninstall"
                         "should be mocked away")
def test_integration_uninstall_all(mocker) -> None:
    """Tests that the uninstall command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be uninstalled"""
    runner = CliRunner()
    mocker.patch('tests.cli.test_integration.uninstall_package',
                 return_value=None)

    result = runner.invoke(integration, ["uninstall"])
    assert result.exit_code == 0
