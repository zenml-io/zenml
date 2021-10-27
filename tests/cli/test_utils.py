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

import click
import pytest
from click.testing import CliRunner
from hypothesis import given
from hypothesis.strategies import text

from zenml.cli.utils import title


@pytest.mark.xfail()
@given(sample_text=text())
def test_title_formats_a_string_properly(sample_text: str) -> None:
    """Check that title function capitalizes text and adds newline"""

    @click.command()
    @click.argument("text")
    def title_trial(text: str) -> None:
        """wrapper function to run title"""
        title(text)

    runner = CliRunner()
    result = runner.invoke(title_trial, [sample_text])
    assert result.output == sample_text.upper() + "\n"


# test all the click.echo9ing of specific comments (style checks)
# test component listing
# test format date
# test format timedelta
# test parsing of unknown CLI options
