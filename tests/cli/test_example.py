#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       http://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import pytest
from click.testing import CliRunner

from zenml import __version__ as running_zenml_version
from zenml.cli.example import info, list, pull

# from hypothesis import given
# from hypothesis.strategies import text


ZERO_FIVE_RELEASE_EXAMPLES = ["airflow", "legacy", "quickstart"]
BAD_VERSIONS = ["aaa", "999999", "111111"]


@pytest.mark.parametrize("example", ZERO_FIVE_RELEASE_EXAMPLES)
def test_list_returns_three_examples_for_0_5_release(example: str) -> None:
    """Check the examples returned from zenml example list"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        result = runner.invoke(list)
        assert result.exit_code == 0
        assert example in result.output


@pytest.mark.parametrize("example", ZERO_FIVE_RELEASE_EXAMPLES)
def test_info_returns_zero_exit_code(example: str) -> None:
    """Check info command exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        result = runner.invoke(info, [example])
        assert result.exit_code == 0


def test_pull_command_returns_zero_exit_code() -> None:
    """Check pull command exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(pull, ["-f", "-v", running_zenml_version])
        assert result.exit_code == 0


def test_pull_earlier_version_returns_zero_exit_code() -> None:
    """Check pull of earlier version exits without errors"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.1"])
        result = runner.invoke(pull, ["-f", "-v", "0.3.8"])
        assert result.exit_code == 0


@pytest.mark.parametrize("bad_version", BAD_VERSIONS)
def test_pull_of_nonexistent_version_fails(bad_version: str) -> None:
    """When trying to pull a version that doesn't exist,
    ZenML handles the failed cloning"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(pull, ["-f", "-v", bad_version])
        assert result.exit_code != 0


def test_pull_of_higher_version_than_currently_in_global_config_store() -> None:
    """Check what happens when (valid) desired version for a force redownload
    is higher than the latest version stored in the global config"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.0"])
        result = runner.invoke(pull, ["-f", "-v", "0.5.1"])
        assert result.exit_code == 0


@pytest.mark.parametrize("bad_version", BAD_VERSIONS)
def test_pull_of_bad_version_when_valid_version_already_exists(
    bad_version: str,
) -> None:
    """When user has valid version present in global config, attempts to force
    redownload invalid versions should fail"""
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(pull, ["-f", "-v", "0.5.1"])
        result = runner.invoke(pull, ["-f", "-v", bad_version])
        assert result.exit_code != 0


# Shouldn't we test here that it pulls properly in all the use-cases we have
# imagined? Like trying to pull first without any flags, then using a pull with
# an older version, then trying to pull from a version that doesn't exist at all?


# Test examples lists all examples for a specific version
# Test info echos out readme content
# Test info fails somehow (predictably?) if we pass in the wrong argument
# test examples pull handles parsing for weird version numbers
# test examples pull on its own
# test examples pull -f on its own
# test examples pull -f -v with an actual version
# test examples pull -f -v with a non-existent version

# add tests for this scenario (user has 0.5.0 as latest version in the global
# config, but wants 0.5.1 (should redownload + try to checkout desired version))
