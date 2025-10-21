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
import platform
from pathlib import Path

import pytest

from tests.integration.functional.cli.utils import cli_runner
from zenml.cli.base import ZENML_PROJECT_TEMPLATES, clean, init
from zenml.constants import CONFIG_FILE_NAME, REPOSITORY_DIRECTORY_NAME
from zenml.utils import yaml_utils
from zenml.utils.io_utils import get_global_config_directory


def test_init_creates_zen_folder(tmp_path: Path) -> None:
    """Check that init command creates a .zen folder."""
    runner = cli_runner()
    result = runner.invoke(init, ["--path", str(tmp_path), "--test"])
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert (tmp_path / REPOSITORY_DIRECTORY_NAME).exists()


@pytest.mark.skipif(
    platform.system().lower() == "windows",
    reason="Windows not fully supported",
)
@pytest.mark.parametrize(
    "template_name",
    list(ZENML_PROJECT_TEMPLATES.keys()),
)
def test_init_creates_from_templates(
    tmp_path: Path, template_name: str
) -> None:
    """Check that init command checks-out template."""
    runner = cli_runner()
    result = runner.invoke(
        init,
        [
            "--path",
            str(tmp_path),
            "--template",
            template_name,
            "--template-with-defaults",
            "--test",
        ],
    )
    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert (tmp_path / REPOSITORY_DIRECTORY_NAME).exists()
    files_in_top_level = set([f.lower() for f in os.listdir(str(tmp_path))])
    must_have_files = {
        ".copier-answers.yml",
        ".dockerignore",
        "license",
        "run.py",
    }
    assert not must_have_files - files_in_top_level


def test_clean_user_config(clean_client) -> None:
    global_zen_config_yaml = (
        Path(get_global_config_directory()) / CONFIG_FILE_NAME
    )
    assert global_zen_config_yaml.exists()
    yaml_contents = yaml_utils.read_yaml(str(global_zen_config_yaml))
    user_id = yaml_contents["user_id"]
    analytics_opt_in = yaml_contents["analytics_opt_in"]
    version = yaml_contents["version"]
    runner = cli_runner()
    result = runner.invoke(clean, ["--yes"])
    assert result.exit_code == 0, f"Command failed: {result.output}"
    new_yaml_contents = yaml_utils.read_yaml(str(global_zen_config_yaml))
    assert user_id == new_yaml_contents["user_id"]
    assert analytics_opt_in == new_yaml_contents["analytics_opt_in"]
    assert version == new_yaml_contents["version"]


def test_clean_calls_store_close(monkeypatch, clean_client) -> None:
    # Import locally to avoid modifying module-level imports
    from zenml.config.global_config import GlobalConfiguration
    from zenml.zen_stores.sql_zen_store import SqlZenStore

    # Track whether close was called
    called = {"closed": False}

    # Keep reference to the original close to preserve behavior
    orig_close = SqlZenStore.close

    def tracked_close(self):
        called["closed"] = True
        # Call through to the original to keep cleanup behavior intact
        return orig_close(self)

    # Patch the close method
    monkeypatch.setattr(SqlZenStore, "close", tracked_close, raising=True)

    # Ensure the store is initialized in this process so there is something to close
    _ = GlobalConfiguration().zen_store

    # Run clean
    result = cli_runner().invoke(clean, ["--yes"])
    assert result.exit_code == 0, f"Command failed: {result.output}"

    # Verify that our close hook was executed
    assert called["closed"] is True
