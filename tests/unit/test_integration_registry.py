#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Tests for the integration registry module."""

import pytest

from zenml.integrations.integration import Integration
from zenml.integrations.registry import IntegrationRegistry


class TestIntegration(Integration):
    """Test integration class with command args."""

    NAME = "test_integration"
    REQUIREMENTS = ["test-package>=1.0.0"]
    INSTALL_COMMAND_ARGS = ["--test-arg", "--another-arg=value"]


class AnotherTestIntegration(Integration):
    """Test integration class without command args."""

    NAME = "another_test_integration"
    REQUIREMENTS = ["another-package>=2.0.0"]
    # Default empty INSTALL_COMMAND_ARGS


def test_integration_install_command_args():
    """Test that install command args are correctly returned by the integration."""
    assert TestIntegration.get_install_command_args() == [
        "--test-arg",
        "--another-arg=value",
    ]
    assert AnotherTestIntegration.get_install_command_args() == []


def test_integration_registry_install_command_args():
    """Test that the integration registry returns correct install command args."""
    # Create a test registry
    registry = IntegrationRegistry()

    # Register our test integrations
    registry.register_integration(TestIntegration.NAME, TestIntegration)
    registry.register_integration(
        AnotherTestIntegration.NAME, AnotherTestIntegration
    )

    # Test getting args for a specific integration
    assert registry.select_integration_install_command_args(
        "test_integration"
    ) == ["--test-arg", "--another-arg=value"]
    assert (
        registry.select_integration_install_command_args(
            "another_test_integration"
        )
        == []
    )

    # Test getting combined args for all integrations
    # The result should be a unique list of all args
    all_args = registry.select_integration_install_command_args()
    assert "--test-arg" in all_args
    assert "--another-arg=value" in all_args
    assert len(all_args) == 2  # No duplicates

    # Test for non-existent integration
    with pytest.raises(KeyError):
        registry.select_integration_install_command_args(
            "non_existent_integration"
        )
