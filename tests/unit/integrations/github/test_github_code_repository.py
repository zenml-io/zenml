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
    symlink_dst = os.path.join(tmp_dir, "test_symlink")
    symlink_src = os.path.join(tmp_dir, "target_folder")

    if initial_state == "file":
        with open(symlink_dst) as file:
            file.write("content")
    elif initial_state == "directory":
        os.mkdir(symlink_dst)
    os.mkdir(symlink_src)

    create_symlink_in_local_repo_copy(
        symlink_dst=symlink_dst, symlink_src=symlink_src
    )
    assert os.path.islink(symlink_dst)
    assert os.readlink(symlink_dst) == str(symlink_src)


def test_create_symlink_in_local_repo_copy_target_nonexistent(tmp_dir, caplog):
    symlink_dst = os.path.join(tmp_dir, "test_symlink")
    symlink_src = os.path.join(tmp_dir, "target_folder")

    with caplog.at_level(logging.WARNING):
        create_symlink_in_local_repo_copy(
            symlink_dst=symlink_dst, symlink_src=symlink_src
        )

    assert not os.path.exists(symlink_dst)
    assert "The target directory of the symbolic link" in caplog.text
