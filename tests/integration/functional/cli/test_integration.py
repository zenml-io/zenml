#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

import sys

import pytest
from click.testing import CliRunner
from pytest_mock import MockFixture

from zenml.cli.integration import integration
from zenml.integrations.registry import integration_registry

NOT_AN_INTEGRATION = ["zenflow", "Anti-Tensorflow", "123"]
INTEGRATIONS = ["airflow", "sklearn", "discord"]


def test_integration_list() -> None:
    """Test that integration list works as expected and lists all
    integrations."""
    runner = CliRunner()

    result = runner.invoke(integration, ["list"])
    assert result.exit_code == 0
    for implemented_integration in integration_registry.integrations:
        assert implemented_integration in result.output


@pytest.mark.parametrize("not_an_integration", NOT_AN_INTEGRATION)
def test_integration_get_requirements_inexistent_integration(
    not_an_integration: str,
) -> None:
    """Tests that the get-requirements sub-command works as expected."""
    runner = CliRunner()

    result = runner.invoke(integration, ["requirements", not_an_integration])
    assert result.exit_code == 1


def test_integration_get_requirements_specific_integration() -> None:
    """Tests that the get-requirements sub-command works as expected."""
    runner = CliRunner()

    result = runner.invoke(integration, ["requirements", "airflow"])
    assert result.exit_code == 0


def test_integration_get_requirements_all() -> None:
    """Tests that the get-requirements sub-command works as expected."""
    runner = CliRunner()

    result = runner.invoke(integration, ["requirements"])
    assert result.exit_code == 0


@pytest.mark.parametrize("not_an_integration", NOT_AN_INTEGRATION)
def test_integration_install_inexistent_integration(
    not_an_integration: str, mocker: MockFixture
) -> None:
    """Tests that the install command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be installed."""
    runner = CliRunner()
    mock_install_package = mocker.patch.object(
        sys.modules["zenml.cli.integration"],
        "install_packages",
        return_value=None,
    )
    result = runner.invoke(integration, ["install", not_an_integration])

    assert result.exit_code == 0
    mock_install_package.assert_not_called()


@pytest.mark.parametrize("integration_name", INTEGRATIONS)
def test_integration_install_specific_integration(
    integration_name: str, mocker: MockFixture
) -> None:
    """Tests that the install command behaves as expected when supplied with
    a specific integration."""
    runner = CliRunner()

    mock_install_package = mocker.patch.object(
        sys.modules["zenml.cli.integration"],
        "install_packages",
        return_value=None,
    )
    mocker.patch(
        "zenml.integrations.registry.IntegrationRegistry.is_installed",
        return_value=False,
    )

    requirements = integration_registry.select_integration_requirements(
        integration_name
    )

    if requirements:
        result = runner.invoke(
            integration, ["install", "-y", integration_name]
        )
        assert result.exit_code == 0
        mock_install_package.assert_called()


def test_integration_install_multiple_integrations(
    mocker: MockFixture,
) -> None:
    """Tests that the install command behaves as expected when supplied with
    multiple integration."""
    runner = CliRunner()

    mock_install_package = mocker.patch.object(
        sys.modules["zenml.cli.integration"],
        "install_packages",
        return_value=None,
    )
    mocker.patch(
        "zenml.integrations.registry.IntegrationRegistry.is_installed",
        return_value=False,
    )

    result = runner.invoke(integration, ["install", "-y", *INTEGRATIONS])
    assert result.exit_code == 0
    mock_install_package.assert_called()


def test_integration_install_all(mocker: MockFixture) -> None:
    """Tests that the install command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be installed."""
    runner = CliRunner()
    mock_install_package = mocker.patch.object(
        sys.modules["zenml.cli.integration"],
        "install_packages",
        return_value=None,
    )
    mocker.patch(
        "zenml.integrations.registry.IntegrationRegistry.is_installed",
        return_value=False,
    )

    result = runner.invoke(integration, ["install", "-y"])
    assert result.exit_code == 0
    mock_install_package.assert_called()


@pytest.mark.parametrize("not_an_integration", NOT_AN_INTEGRATION)
def test_integration_uninstall_inexistent_integration(
    not_an_integration: str, mocker: MockFixture
) -> None:
    """Tests that the install command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be installed."""
    runner = CliRunner()
    mock_uninstall_package = mocker.patch.object(
        sys.modules["zenml.cli.integration"],
        "uninstall_package",
        return_value=None,
    )
    result = runner.invoke(integration, ["uninstall", not_an_integration])
    assert result.exit_code == 0
    mock_uninstall_package.assert_not_called()


@pytest.mark.parametrize("integration_name", INTEGRATIONS)
def test_integration_uninstall_specific_integration(
    integration_name: str, mocker: MockFixture
) -> None:
    """Tests that the uninstall command behaves as expected when supplied with
    a specific integration."""
    runner = CliRunner()
    mock_uninstall_package = mocker.patch.object(
        sys.modules["zenml.cli.integration"],
        "uninstall_package",
        return_value=None,
    )
    mocker.patch(
        "zenml.integrations.registry.IntegrationRegistry.is_installed",
        return_value=True,
    )

    requirements = integration_registry.select_integration_requirements(
        integration_name
    )

    if requirements:
        # We can only execute this test, if the integration has requirements
        result = runner.invoke(
            integration, ["uninstall", "-y", integration_name]
        )
        assert result.exit_code == 0
        mock_uninstall_package.assert_called()


def test_integration_uninstall_all(mocker: MockFixture) -> None:
    """Tests that the uninstall command behaves as expected when supplied with
    no specific integration. This should lead to all packages for all
    integrations to be uninstalled."""
    runner = CliRunner()
    mock_uninstall_package = mocker.patch.object(
        sys.modules["zenml.cli.integration"],
        "uninstall_package",
        return_value=None,
    )
    mocker.patch(
        "zenml.integrations.registry.IntegrationRegistry.is_installed",
        return_value=True,
    )

    result = runner.invoke(integration, ["uninstall", "-y"])
    assert result.exit_code == 0
    mock_uninstall_package.assert_called()


def test_integration_requirements_exporting(tmp_path) -> None:
    """Tests requirements exporting to stdout and to a file."""
    from zenml.integrations.airflow import AirflowIntegration
    from zenml.integrations.kubeflow import KubeflowIntegration
    from zenml.integrations.mlflow import MlflowIntegration

    flow_integration_requirements = set(
        AirflowIntegration.get_requirements()
        + KubeflowIntegration.get_requirements()
        + MlflowIntegration.get_requirements()
    )

    command = [
        "export-requirements",
        AirflowIntegration.NAME,
        KubeflowIntegration.NAME,
        MlflowIntegration.NAME,
    ]
    runner = CliRunner()
    result = runner.invoke(integration, command)
    assert result.exit_code == 0
    assert set(result.output.split(" ")) == flow_integration_requirements

    output_file = str(tmp_path / "requirements.txt")
    command += ["--output-file", output_file]

    result = runner.invoke(integration, command)
    assert result.exit_code == 0

    with open(output_file, "r") as f:
        assert (
            set(f.read().strip().split("\n")) == flow_integration_requirements
        )
