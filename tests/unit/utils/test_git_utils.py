#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Unit tests for git utils."""

import pytest

from zenml.utils.git_utils import clone_git_repository


def test_clone_git_repository(tmp_path):
    """Test correctly cloning a git repository.

    This clones the latest commit of the ZenML repo's main branch in four
    different ways and checks that the resulting repos are identical.
    """
    repo1 = clone_git_repository(
        url="https://github.com/zenml-io/zenml",
        to_path=f"{tmp_path}/zenml",
    )
    assert repo1 is not None
    assert repo1.head.shorthand == "main"
    assert repo1.head.commit is not None

    repo2 = clone_git_repository(
        url="https://github.com/zenml-io/zenml",
        to_path=f"{tmp_path}/zenml2",
        branch="main",
    )
    assert repo2 is not None
    assert repo2.head.shorthand == "main"
    assert repo1.head.commit == repo2.head.commit

    repo3 = clone_git_repository(
        url="https://github.com/zenml-io/zenml",
        to_path=f"{tmp_path}/zenml3",
        commit=repo1.head.commit.hexsha,
    )
    assert repo3 is not None
    assert repo3.head.shorthand == "main"
    assert repo1.head.commit == repo3.head.commit

    repo4 = clone_git_repository(
        url="https://github.com/zenml-io/zenml",
        to_path=f"{tmp_path}/zenml2",
        branch="main",
        commit=repo1.head.commit.hexsha,
    )
    assert repo4 is not None
    assert repo4.head.shorthand == "main"
    assert repo1.head.commit == repo4.head.commit


def test_clone_git_repository_with_commit(tmp_path):
    """Test correctly cloning a git repository from a specific commit."""
    commit = "849d323139f3f4e3a8a2ca84a97fe225f9dfe7ce"  # 0.20.0
    repo = clone_git_repository(
        url="https://github.com/zenml-io/zenml",
        to_path=f"{tmp_path}/zenml",
        commit=commit,
    )
    assert repo is not None
    assert repo.head.shorthand == "main"
    assert repo.head.commit.hexsha == commit


def test_clone_git_repository_with_branch(tmp_path):
    """Test correctly cloning a git repository from a specific branch."""
    commit = "a1cdbe2da945e3a94805ca7db651a1b03b2c8b1f"  # 0.30.0
    repo = clone_git_repository(
        url="https://github.com/zenml-io/zenml",
        to_path=f"{tmp_path}/zenml",
        branch="release/0.30.0",
    )
    assert repo is not None
    assert repo.head.shorthand == "release/0.30.0"
    assert repo.head.commit.hexsha == commit


def test_clone_git_repository_with_branch_and_commit(tmp_path):
    """Test that cloning from commit overrides branch."""
    commit = "849d323139f3f4e3a8a2ca84a97fe225f9dfe7ce"  # 0.20.0
    repo = clone_git_repository(
        url="https://github.com/zenml-io/zenml",
        to_path=f"{tmp_path}/zenml",
        branch="release/0.30.0",
        commit=commit,
    )
    assert repo is not None
    assert repo.head.shorthand == "main"
    assert repo.head.commit.hexsha == commit


@pytest.mark.parametrize(
    "invalid_url",
    [
        "",
        "https://google.com/zenml-io/zenml",
        "https://github.com",
        "https://github.com/zenml-io",
    ],
)
def test_clone_git_repository_with_invalid_url(tmp_path, invalid_url):
    """Test that cloning from invalid URL fails."""
    with pytest.raises(RuntimeError):
        clone_git_repository(
            url=invalid_url,
            to_path=f"{tmp_path}/zenml",
        )


def test_clone_git_repository_with_invalid_commit(tmp_path):
    """Test that cloning from invalid commit fails."""
    with pytest.raises(RuntimeError):
        clone_git_repository(
            url="https://github.com/zenml-io/zenml",
            to_path=f"{tmp_path}/zenml",
            commit="thisisnotavalidcommit",
        )


def test_clone_git_repository_with_invalid_branch(tmp_path):
    """Test that cloning from invalid branch fails."""
    with pytest.raises(RuntimeError):
        clone_git_repository(
            url="https://github.com/zenml-io/zenml",
            to_path=f"{tmp_path}/zenml",
            branch="thisisnotavalidbranch",
        )
