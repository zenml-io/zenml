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

import pytest
from click.testing import CliRunner

from zenml.cli.example import info, list, pull

ZERO_FIVE_RELEASE_EXAMPLES = ["airflow", "legacy", "quickstart"]


@pytest.mark.parametrize("example", ZERO_FIVE_RELEASE_EXAMPLES)
def test_list_returns_three_examples_for_0_5_release(example: str) -> None:
    """Check the examples returned from zenml example list"""
    runner = CliRunner()
    runner.invoke(pull, ["--force-redownload", "0.5.0"])
    with runner.isolated_filesystem():
        result = runner.invoke(list)
        assert result.exit_code == 0
        assert example in result.output


@pytest.mark.parametrize("example", ZERO_FIVE_RELEASE_EXAMPLES)
def test_info_returns_zero_exit_code(example: str) -> None:
    """Check info command exits without errors"""
    runner = CliRunner()
    result = runner.invoke(info, [example])
    assert result.exit_code == 0


def test_pull_command_returns_zero_exit_code() -> None:
    """Check pull command exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(pull)
        assert result.exit_code == 0
