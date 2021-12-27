#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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


import pytest
from click.testing import CliRunner

from zenml.cli.orchestrator import describe_orchestrator

NOT_ORCHESTRATORS = ["abc", "my_other_cat_is_called_blupus", "orchestrator123"]


def test_orchestrator_describe_contains_local_orchestrator() -> None:
    """Test that the orchestrator describe command contains the default local orchestrator"""
    # TODO [HIGH]: add a fixture that spins up a test env each time
    runner = CliRunner()
    result = runner.invoke(describe_orchestrator)
    assert result.exit_code == 0
    assert "local_orchestrator" in result.output


@pytest.mark.parametrize("not_an_orchestrator", NOT_ORCHESTRATORS)
def test_orchestrator_describe_fails_for_bad_input(
    not_an_orchestrator: str,
) -> None:
    """Test that the orchestrator describe command fails when passing in bad parameters"""
    # TODO [HIGH]: add a fixture that spins up a test env each time
    runner = CliRunner()
    result = runner.invoke(describe_orchestrator, [not_an_orchestrator])
    assert result.exit_code == 1
