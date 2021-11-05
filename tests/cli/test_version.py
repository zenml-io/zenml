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

from click.testing import CliRunner

from zenml import __version__ as current_zenml_version
from zenml.cli.version import version


def test_version_outputs_running_version_number() -> None:
    """Checks that CLI version command works"""
    runner = CliRunner()
    result = runner.invoke(version)
    assert result.exit_code == 0
    assert current_zenml_version in result.output
