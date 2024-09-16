import logging
import os
from tempfile import TemporaryDirectory

import pytest

from zenml.integrations.github.code_repositories.github_code_repository import (
    create_symlink_in_local_repo_copy,
)


@pytest.fixture()
def tmp_dir() -> str:
    with TemporaryDirectory() as tmp:
        yield tmp


@pytest.mark.parametrize("initial_state", ["file", "directory"])
def test_create_symlink_in_local_repo_copy(tmp_dir, initial_state: str):
    local_path = os.path.join(tmp_dir, "test_symlink")
    symlink_target = os.path.join(tmp_dir, "target_folder")

    if initial_state == "file":
        with open(local_path) as file:
            file.write("content")
    elif initial_state == "directory":
        os.mkdir(local_path)
    os.mkdir(symlink_target)

    create_symlink_in_local_repo_copy(
        symlink_source=local_path, symlink_target=symlink_target
    )
    assert os.path.islink(local_path)
    assert os.readlink(local_path) == str(symlink_target)


def test_create_symlink_in_local_repo_copy_target_nonexistent(tmp_dir, caplog):
    local_path = os.path.join(tmp_dir, "test_symlink")
    symlink_target = os.path.join(tmp_dir, "target_folder")

    with caplog.at_level(logging.WARNING):
        create_symlink_in_local_repo_copy(
            symlink_source=local_path, symlink_target=symlink_target
        )

    assert not os.path.exists(local_path)
    assert "The target directory of the symbolic link" in caplog.text
