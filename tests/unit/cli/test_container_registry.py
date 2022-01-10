#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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


import pytest
from click.testing import CliRunner

from zenml.cli.container_registry import (
    delete_container_registry,
    describe_container_registry,
    register_container_registry,
)

NOT_CONTAINER_REGISTRIES = [
    "abc",
    "my_other_cat_is_called_blupus",
    "container_registry_123",
]


def test_container_registry_describe_fails_gracefully_when_no_registry_present() -> None:
    """Test that the container_registry describe command fails when no registry present (as per default)"""
    # TODO [HIGH]: add a fixture that spins up a test env each time
    runner = CliRunner()
    result = runner.invoke(describe_container_registry)
    assert result.exit_code == 0
    assert "No container registries registered!" in result.output


@pytest.mark.parametrize("not_a_container_registry", NOT_CONTAINER_REGISTRIES)
def test_container_registry_describe_works(
    not_a_container_registry: str,
) -> None:
    """Test that the container_registry describe command works when passing in correct parameters"""
    # TODO [HIGH]: add a fixture that spins up a test env each time
    runner = CliRunner()
    runner.invoke(
        register_container_registry, [not_a_container_registry, "some_uri"]
    )
    result = runner.invoke(
        describe_container_registry, [not_a_container_registry]
    )
    assert result.exit_code == 0
    runner.invoke(delete_container_registry, [not_a_container_registry])
