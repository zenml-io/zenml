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

import os
from pathlib import Path

from click.testing import CliRunner

from zenml.cli.base import clean, init
from zenml.constants import CONFIG_FILE_NAME, REPOSITORY_DIRECTORY_NAME
from zenml.utils import yaml_utils
from zenml.utils.io_utils import get_global_config_directory


def test_init_creates_zen_folder(tmp_path: Path) -> None:
    """Check that init command creates a .zen folder."""
    runner = CliRunner()
    runner.invoke(init, ["--path", str(tmp_path)])
    assert (tmp_path / REPOSITORY_DIRECTORY_NAME).exists()


def test_init_creates_from_template(tmp_path: Path) -> None:
    """Check that init command checks-out template."""
    runner = CliRunner()
    runner.invoke(
        init,
        [
            "--path",
            str(tmp_path),
            "--template",
            "e2e_batch",
            "--template-with-defaults",
        ],
    )
    assert (tmp_path / REPOSITORY_DIRECTORY_NAME).exists()
    files_in_top_level = set(os.listdir(str(tmp_path)))
    must_have_files = {
        ".copier-answers.yml",
        ".dockerignore",
        "LICENSE",
        "README.md",
        "run.py",
    }
    assert not must_have_files - files_in_top_level


def test_clean_user_config(clean_workspace) -> None:
    global_zen_config_yaml = (
        Path(get_global_config_directory()) / CONFIG_FILE_NAME
    )
    assert global_zen_config_yaml.exists()
    yaml_contents = yaml_utils.read_yaml(str(global_zen_config_yaml))
    user_id = yaml_contents["user_id"]
    analytics_opt_in = yaml_contents["analytics_opt_in"]
    version = yaml_contents["version"]
    runner = CliRunner()
    runner.invoke(clean, ["--yes", True])
    new_yaml_contents = yaml_utils.read_yaml(str(global_zen_config_yaml))
    assert user_id == new_yaml_contents["user_id"]
    assert analytics_opt_in == new_yaml_contents["analytics_opt_in"]
    assert version == new_yaml_contents["version"]
