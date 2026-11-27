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
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from git import Repo

from zenml.utils.code_utils import CodeArchive


@pytest.mark.parametrize(
    "filename",
    [
        "my step.py",
        "model assets/weights.bin",
        "caf\u00e9.py",
        "\u6a21\u578b.py",
    ],
)
@pytest.mark.parametrize("tracked", [False, True])
def test_get_files_preserves_git_filenames(
    tmp_path: Path, filename: str, tracked: bool
) -> None:
    """Check that Git-backed archives preserve complete filenames.

    Args:
        tmp_path: Temporary directory for the Git repository.
        filename: Filename to include in the code archive.
        tracked: Whether to stage the file in Git.
    """
    repo = Repo.init(tmp_path)
    file_path = tmp_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"pipeline data")
    if tracked:
        repo.index.add([filename])

    files = CodeArchive(root=str(tmp_path)).get_files()
    assert {name: Path(path) for name, path in files.items()} == {
        os.path.normpath(filename): file_path
    }


def test_code_archive_preserves_git_file_contents(tmp_path: Path) -> None:
    """Check packaged contents and ignore rules with a real Git repository.

    Args:
        tmp_path: Temporary directory for the repository and output archive.
    """
    root = tmp_path / "repo"
    root.mkdir()
    repo = Repo.init(root)
    (root / ".gitignore").write_text("ignored.bin\n")
    (root / "ignored.bin").write_bytes(b"ignored")
    (root / "tracked step.py").write_bytes(b"original")
    repo.index.add([".gitignore", "tracked step.py"])
    (root / "tracked step.py").write_bytes(b"modified")
    (root / "new model.bin").write_bytes(b"\x00\xff\x01")
    (root / ".zen").mkdir()
    (root / ".zen" / "config.yaml").write_text("local configuration")

    archive_path = tmp_path / "code.tar.gz"
    with archive_path.open("w+b") as output:
        CodeArchive(root=str(root)).write_archive(output)

    with tarfile.open(archive_path) as archive:
        assert set(archive.getnames()) == {
            ".gitignore",
            "tracked step.py",
            "new model.bin",
        }
        for filename, contents in {
            "tracked step.py": b"modified",
            "new model.bin": b"\x00\xff\x01",
        }.items():
            extracted = archive.extractfile(filename)
            assert extracted is not None
            assert extracted.read() == contents


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
            "main.py\0external/lib.py\0",
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
    assert "-z" in first_call_args

    second_call_args = mock_repo.git.ls_files.call_args_list[1][0]
    assert "--others" in second_call_args
    assert "--modified" in second_call_args
    assert "--recurse-submodules" not in second_call_args
    assert "-z" in second_call_args

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
            "tracked.py\0",
            "new_file.py\0",
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
