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

from zenml.cli.artifact_store import describe_artifact_store

NOT_ARTIFACT_STORES = [
    "abc",
    "my_other_cat_is_called_blupus",
    "orchestrator123",
]


def test_artifact_describe_contains_local_orchestrator() -> None:
    """Test that the artifact describe command contains the default local artifact store"""
    # TODO [ENG-333]: add a fixture that spins up a test env each time
    runner = CliRunner()
    result = runner.invoke(describe_artifact_store)
    assert result.exit_code == 0
    assert "local_artifact_store" in result.output


@pytest.mark.parametrize("not_an_artifact_store", NOT_ARTIFACT_STORES)
def test_artifact_describe_fails_for_bad_input(
    not_an_artifact_store: str,
) -> None:
    """Test that the artifact describe command fails when passing in bad parameters"""
    # TODO [ENG-334]: add a fixture that spins up a test env each time
    runner = CliRunner()
    result = runner.invoke(describe_artifact_store, [not_an_artifact_store])
    assert result.exit_code == 1
