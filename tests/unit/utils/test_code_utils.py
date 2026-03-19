#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Unit tests for code_utils.py."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

from zenml.utils.code_utils import CodeArchive


def test_get_files_uses_recurse_submodules(tmp_path):
    """Verify that git ls-files is called with --recurse-submodules for
    tracked files and a separate call for untracked/modified files."""
    # Create a file on disk so os.path.exists passes
    test_file = tmp_path / "main.py"
    test_file.write_text("print('hello')")
    submodule_file = tmp_path / "external" / "lib.py"
    submodule_file.parent.mkdir()
    submodule_file.write_text("x = 1")

    mock_repo = MagicMock()
    mock_repo.working_dir = str(tmp_path)

    # First call: --cached --recurse-submodules returns tracked + submodule
    # Second call: --others --modified returns nothing extra
    mock_repo.git.ls_files = MagicMock(
        side_effect=[
            "main.py\nexternal/lib.py",
            "",
        ]
    )

    archive = CodeArchive(root=str(tmp_path))

    with patch.object(
        CodeArchive, "git_repo", new_callable=PropertyMock
    ) as mock_git_repo:
        mock_git_repo.return_value = mock_repo
        files = archive.get_files()

    # Both tracked calls should have been made
    assert mock_repo.git.ls_files.call_count == 2

    first_call_args = mock_repo.git.ls_files.call_args_list[0][0]
    assert "--recurse-submodules" in first_call_args
    assert "--cached" in first_call_args

    second_call_args = mock_repo.git.ls_files.call_args_list[1][0]
    assert "--others" in second_call_args
    assert "--modified" in second_call_args
    assert "--recurse-submodules" not in second_call_args

    assert "main.py" in files
    assert os.path.join("external", "lib.py") in files


def test_get_files_includes_untracked_files(tmp_path):
    """Verify that untracked/modified files from the second ls-files call
    are included in the archive."""
    tracked = tmp_path / "tracked.py"
    tracked.write_text("tracked")
    untracked = tmp_path / "new_file.py"
    untracked.write_text("untracked")

    mock_repo = MagicMock()
    mock_repo.working_dir = str(tmp_path)
    mock_repo.git.ls_files = MagicMock(
        side_effect=[
            "tracked.py",
            "new_file.py",
        ]
    )

    archive = CodeArchive(root=str(tmp_path))

    with patch.object(
        CodeArchive, "git_repo", new_callable=PropertyMock
    ) as mock_git_repo:
        mock_git_repo.return_value = mock_repo
        files = archive.get_files()

    assert "tracked.py" in files
    assert "new_file.py" in files


def test_get_files_falls_back_on_git_error(tmp_path):
    """Verify that if git ls-files fails, all files are included via
    the filesystem fallback."""
    test_file = tmp_path / "fallback.py"
    test_file.write_text("fallback")

    mock_repo = MagicMock()
    mock_repo.working_dir = str(tmp_path)
    mock_repo.git.ls_files = MagicMock(side_effect=Exception("git error"))

    archive = CodeArchive(root=str(tmp_path))

    with patch.object(
        CodeArchive, "git_repo", new_callable=PropertyMock
    ) as mock_git_repo:
        mock_git_repo.return_value = mock_repo
        files = archive.get_files()

    assert "fallback.py" in files
