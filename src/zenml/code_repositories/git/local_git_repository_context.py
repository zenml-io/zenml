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
"""Implementation of the Local git repository context."""

from typing import TYPE_CHECKING, Callable, Optional, cast
from uuid import UUID

from zenml.code_repositories import (
    LocalRepositoryContext,
)
from zenml.logger import get_logger

if TYPE_CHECKING:
    from git.objects import Commit
    from git.remote import Remote
    from git.repo.base import Repo

logger = get_logger(__name__)


class LocalGitRepositoryContext(LocalRepositoryContext):
    """Local git repository context."""

    def __init__(
        self, code_repository_id: UUID, git_repo: "Repo", remote_name: str
    ):
        """Initializes a local git repository context.

        Args:
            code_repository_id: The ID of the code repository.
            git_repo: The git repo.
            remote_name: Name of the remote.
        """
        super().__init__(code_repository_id=code_repository_id)
        self._git_repo = git_repo
        self._remote = git_repo.remote(name=remote_name)

    @classmethod
    def at(
        cls,
        path: str,
        code_repository_id: UUID,
        remote_url_validation_callback: Callable[[str], bool],
    ) -> Optional["LocalGitRepositoryContext"]:
        """Returns a local git repository at the given path.

        Args:
            path: The path to the local git repository.
            code_repository_id: The ID of the code repository.
            remote_url_validation_callback: A callback that validates the
                remote URL of the git repository.

        Returns:
            A local git repository if the path is a valid git repository
            and the remote URL is valid, otherwise None.
        """
        try:
            # These imports fail when git is not installed on the machine
            from git.exc import InvalidGitRepositoryError
            from git.repo.base import Repo
        except ImportError:
            return None

        try:
            git_repo = Repo(path=path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            return None

        remote_name = None
        for remote in git_repo.remotes:
            if remote_url_validation_callback(remote.url):
                remote_name = remote.name
                break

        if not remote_name:
            return None

        return LocalGitRepositoryContext(
            code_repository_id=code_repository_id,
            git_repo=git_repo,
            remote_name=remote_name,
        )

    @property
    def git_repo(self) -> "Repo":
        """The git repo.

        Returns:
            The git repo object of the local git repository.
        """
        return self._git_repo

    @property
    def remote(self) -> "Remote":
        """The git remote.

        Returns:
            The remote of the git repo object of the local git repository.
        """
        return self._remote

    @property
    def root(self) -> str:
        """The root of the git repo.

        Returns:
            The root of the git repo.
        """
        assert self.git_repo.working_dir
        return str(self.git_repo.working_dir)

    @property
    def is_dirty(self) -> bool:
        """Whether the git repo is dirty.

        A repository counts as dirty if it has any untracked or uncommitted
        changes.

        Returns:
            True if the git repo is dirty, False otherwise.
        """
        return self.git_repo.is_dirty(untracked_files=True)

    @property
    def has_local_changes(self) -> bool:
        """Whether the git repo has local changes.

        A repository has local changes if it is dirty or there are some commits
        which have not been pushed yet.

        Returns:
            True if the git repo has local changes, False otherwise.

        Raises:
            RuntimeError: If the git repo is in a detached head state.
        """
        if self.is_dirty:
            return True

        self.remote.fetch()

        local_commit_object = self.git_repo.head.commit
        try:
            active_branch = self.git_repo.active_branch
        except TypeError:
            raise RuntimeError(
                "Git repo in detached head state is not allowed."
            )

        try:
            remote_commit_object = self.remote.refs[active_branch.name].commit
        except IndexError:
            # Branch doesn't exist on remote
            return True

        return cast("Commit", remote_commit_object) != local_commit_object

    @property
    def current_commit(self) -> str:
        """The current commit.

        Returns:
            The current commit sha.
        """
        return cast(str, self.git_repo.head.object.hexsha)
