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

import os

from click.testing import CliRunner
from git import Repo

from zenml.cli.base import init
from zenml.core.constants import ZENML_DIR_NAME


def test_init_creates_zen_folder(tmp_path):
    """Check that init command creates a .zen folder inside temporary directory"""
    runner = CliRunner()
    Repo.init(tmp_path, mkdir=True)
    repository_path = tmp_path
    runner.invoke(init, ["--repo_path", str(repository_path)])
    dir_files = os.listdir(repository_path)
    assert ZENML_DIR_NAME in dir_files
