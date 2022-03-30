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

from pathlib import Path

from click.testing import CliRunner

from zenml.cli.base import init
from zenml.constants import REPOSITORY_DIRECTORY_NAME


def test_init_creates_zen_folder(tmp_path: Path) -> None:
    """Check that init command creates a .zen folder."""
    runner = CliRunner()
    runner.invoke(init, ["--path", str(tmp_path)])
    assert (tmp_path / REPOSITORY_DIRECTORY_NAME).exists()
