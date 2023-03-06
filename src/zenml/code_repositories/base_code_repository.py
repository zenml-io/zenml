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
import os
import re
from abc import ABC, abstractmethod
from typing import Callable, Optional, Type, TypeVar, cast
from uuid import UUID

from git.repo.base import Remote, Repo
from github import Github, GithubException, Repository

from zenml.logger import get_logger
from zenml.models.code_repository_models import CodeRepositoryResponseModel
from zenml.utils import source_utils_v2

logger = get_logger(__name__)


class LocalRepository(ABC):
    def __init__(
        self, zenml_code_repository: "BaseCodeRepository", *args, **kwargs
    ) -> None:
        self._zenml_code_repository = zenml_code_repository

    @property
    def zenml_code_repository(self) -> "BaseCodeRepository":
        return self._zenml_code_repository

    @property
    @abstractmethod
    def root(self) -> str:
        pass

    @property
    @abstractmethod
    def is_dirty(self) -> bool:
        # uncommited changes
        pass

    @property
    @abstractmethod
    def has_local_changes(self) -> bool:
        # uncommited or unpushed changes
        pass

    @property
    @abstractmethod
    def current_commit(self) -> str:
        pass


C = TypeVar("C", bound="BaseCodeRepository")


class BaseCodeRepository(ABC):
    def __init__(self, id: UUID) -> None:
        self._id = id

    @classmethod
    def from_model(
        cls: Type[C], model: CodeRepositoryResponseModel
    ) -> "BaseCodeRepository":
        class_: Type[
            BaseCodeRepository
        ] = source_utils_v2.load_and_validate_class(
            source=model.source, expected_class=BaseCodeRepository
        )
        return class_(id=model.id, **model.config)

    @property
    def id(self) -> UUID:
        return self._id

    @abstractmethod
    def login(self) -> None:
        pass

    @abstractmethod
    def download_files(
        self, commit: str, directory: str, repo_sub_directory: Optional[str]
    ) -> None:
        # download files of commit to local directory
        pass

    @abstractmethod
    def get_local_repo(self, path: str) -> Optional[LocalRepository]:
        pass

    def exists_at_path(self, path: str) -> bool:
        return self.get_local_repo(path=path) is not None


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


class GitHubCodeRepository(BaseCodeRepository):
    """GitHub code repository."""

    _github_session: Github

    def __init__(self, id: UUID, owner: str, repository: str, token: str):
        """Initializes a GitHub code repository.

        Args:
            id: The id of the code repository.
            owner: The owner of the repository.
            repository: The name of the repository.
            token: The GitHub token.
        """
        super().__init__(id=id)
        self._owner = owner
        self._repository = repository
        self._token = token

    @property
    def github_repo(self) -> Repository:
        """The GitHub repository."""
        return self._github_session.get_repo(
            f"{self._owner}/{self._repository}"
        )

    def login(
        self,
    ) -> None:
        """Logs in to GitHub."""
        try:
            self._github_session = Github(self._token)
            user = self._github_session.get_user().login
            logger.debug(f"Logged in as {user}")
        except Exception as e:
            raise RuntimeError(
                f'f"An error occurred while logging in: {str(e)}'
            )

    def download_files(
        self, commit: str, directory: str, repo_sub_directory: Optional[str]
    ) -> None:
        """Downloads files from a commit to a local directory.

        Args:
            commit: The commit to download.
            directory: The directory to download to.
            repo_sub_directory: The sub directory to download from.
        """
        contents = self.github_repo.get_dir_contents(
            repo_sub_directory, ref=commit
        )
        for content in contents:
            logger.debug(f"Processing {content.path}")
            if content.type == "dir":
                path = os.path.join(directory, content.name)
                os.makedirs(path, exist_ok=True)
                self.download_files(
                    commit=commit,
                    directory=path,
                    repo_sub_directory=content.path,
                )
            else:
                try:
                    path = content.path
                    content_file = self.github_repo.get_contents(
                        path, ref=commit
                    )
                    data = content_file.decoded_content
                    path = os.path.join(directory, content.name)
                    with open(path, "wb") as file:
                        file.write(data)
                    file.close()
                except (GithubException, IOError) as e:
                    logger.error("Error processing %s: %s", content.path, e)

    def get_local_repo(self, path: str) -> LocalRepository:
        """Gets the local repository.

        Args:
            path: The path to the local repository.

        Returns:
            The local repository.
        """
        # TODO: correctly initialize the local git repo, catch potential errors
        try:
            local_git_repo = LocalGitRepository(
                zenml_code_repository=self,
                path=path,
                validate_remote_url=self.check_remote_url,
            )
        except Exception as e:
            logger.info(f"Could not initialize local git repository: {str(e)}")
            return None
        if local_git_repo.is_dirty or local_git_repo.has_local_changes:
            logger.info(
                f"Local git repository has uncommitted or unpushed changes"
            )
        return local_git_repo

    def check_remote_url(self, owner: str, repository: str, url: str) -> bool:
        """Checks whether the remote url is correct.

        Args:
            owner: The owner of the repository.
            repository: The name of the repository.
            url: The remote url.

        Returns:
            Whether the remote url is correct.
        """
        https_url = f"https://github.com/{owner}/{repository}.git"
        if url == https_url:
            return True

        ssh_regex = re.compile(f".*@github.com:{owner}/{repository}.git")
        if ssh_regex.fullmatch(url):
            return True

        return False


class _DownloadedRepository(LocalRepository):
    def __init__(
        self,
        zenml_code_repository: "BaseCodeRepository",
        commit: str,
        root: str,
    ):
        super().__init__(zenml_code_repository=zenml_code_repository)
        self._commit = commit
        self._root = root

    @property
    def root(self) -> str:
        return self._root

    @property
    def is_dirty(self) -> bool:
        return False

    @property
    def has_local_changes(self) -> bool:
        return False

    @property
    def current_commit(self) -> str:
        return self._commit
