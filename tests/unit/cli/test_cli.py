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

import click
import pytest
from click.core import Group
from click.testing import CliRunner

from zenml.cli.cli import ZenMLCLI, cli
from zenml.cli.formatter import ZenFormatter


@pytest.fixture(scope="function")
def runner(request):
    return CliRunner()


def test_cli_command_defines_a_cli_group() -> None:
    """Check that cli command defines a CLI group when invoked"""
    assert isinstance(cli, Group)


def test_cli(runner):
    """Check that basic cli call works"""
    result = runner.invoke(cli)
    assert not result.exception
    assert result.exit_code == 0


def test_cli_help(runner):
    """Check that help works"""
    result = runner.invoke(cli, ["--help"])
    assert not result.exception
    assert "Available Commands By Group Category for Zenml:" in result.output
    assert result.exit_code == 0


def test_ZenMLCLI_formatter():
    """
    Test the ZenFormatter class.
    """
    zencli = ZenMLCLI()
    context = click.Context(zencli)
    formatter = ZenFormatter(context)
    assert isinstance(formatter, ZenFormatter)
