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
"""Utility function to clone a Git repository."""

import os
from typing import Optional

from git import GitCommandError
from git.repo import Repo


def clone_git_repository(
    url: str,
    to_path: str,
    branch: Optional[str] = None,
    commit: Optional[str] = None,
) -> Repo:
    """Clone a Git repository.

    Args:
        url: URL of the repository to clone.
        to_path: Path to clone the repository to.
        branch: Branch to clone. Defaults to "main".
        commit: Commit to checkout. If specified, the branch argument is
            ignored.

    Returns:
        The cloned repository.

    Raises:
        RuntimeError: If the repository could not be cloned.
    """
    os.makedirs(os.path.basename(to_path), exist_ok=True)
    try:
        if commit:
            repo = Repo.clone_from(
                url=url,
                to_path=to_path,
                no_checkout=True,
            )
            repo.git.checkout(commit)
        else:
            repo = Repo.clone_from(
                url=url,
                to_path=to_path,
                branch=branch or "main",
            )
        return repo
    except GitCommandError as e:
        raise RuntimeError from e
