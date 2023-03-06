#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the ZenML local local code repository."""
from typing import Callable, cast

from git.repo.base import Remote, Repo

from zenml.code_repositories.base_code_repository import (
    BaseCodeRepository,
    LocalRepository,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class LocalGitRepository(LocalRepository):
    """Local git repository."""

    def __init__(
        self,
        zenml_code_repository: "BaseCodeRepository",
        path: str,
        validate_remote_url: Callable[[str], bool],
    ):
        """Initializes a local git repository.

        Args:
            zenml_code_repository: The ZenML code repository.
            path: The path to the local git repository.
            validate_remote_url: A function that validates the remote url.
        """
        super().__init__(zenml_code_repository=zenml_code_repository)
        self._git_repo = Repo(path=path, search_parent_directories=True)
        # TODO: write function that get's the correct remote based on url
        for remote in self._git_repo.remotes:
            if validate_remote_url(
                zenml_code_repository._owner,
                zenml_code_repository._repository,
                remote.url,
            ):
                self._remote = remote
                break
        if not self._remote:
            raise ValueError(
                f"No remote found for the given owner: {zenml_code_repository._owner} and repository: {zenml_code_repository._repository}."
            )

    @property
    def git_repo(self) -> Repo:
        """The git repo."""
        return self._git_repo

    @property
    def remote(self) -> Remote:
        """The remote."""
        return self._remote

    @property
    def root(self) -> str:
        """The root of the git repo."""
        assert self.git_repo.working_dir
        return str(self.git_repo.working_dir)

    @property
    def is_dirty(self) -> bool:
        """Whether the git repo is dirty."""
        return self.git_repo.is_dirty(untracked_files=True)

    @property
    def has_local_changes(self) -> bool:
        """Whether the git repo has local changes."""
        if self.is_dirty:
            return True

        self.remote.fetch()

        local_commit = self.git_repo.head.commit
        try:
            active_branch = self.git_repo.active_branch
        except TypeError:
            raise RuntimeError(
                "Git repo in detached head state is not allowed."
            )

        try:
            remote_commit = self.remote.refs[active_branch.name].commit
        except IndexError:
            # Branch doesn't exist on remote
            return True

        return remote_commit != local_commit

    @property
    def current_commit(self) -> str:
        """The current commit."""
        return cast(str, self.git_repo.head.object.hexsha)
