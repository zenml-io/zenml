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
import re
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, TypeVar, cast
from uuid import UUID

from git.repo.base import Remote, Repo

from zenml.logger import get_logger
from zenml.models.code_repository_models import CodeRepositoryResponseModel
from zenml.utils import source_utils_v2

logger = get_logger(__name__)


class LocalRepository(ABC):
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
    def __init__(self, id: UUID, **kwargs: Any) -> None:
        self._id = id

    @classmethod
    def from_model(cls: Type[C], model: CodeRepositoryResponseModel) -> C:
        class_: Type[
            BaseCodeRepository
        ] = source_utils_v2.load_and_validate_class(
            source=model.source, expected_class=BaseCodeRepository
        )
        return class_(**model.config)

    @property
    def id(self) -> UUID:
        return self._id

    @abstractmethod
    def login(self) -> None:
        pass

    @abstractmethod
    def download_files(self, commit: str, directory: str) -> None:
        # download files of commit to local directory
        pass

    @abstractmethod
    def get_local_repo(self, path: str) -> Optional[LocalRepository]:
        pass

    def exists_at_path(self, path: str) -> bool:
        return self.get_local_repo(path=path) is not None


class LocalGitRepository(LocalRepository):
    # TODO: this maybe needs to accept a callback which checks if the remote
    # URL matches? E.g. the ssh remote url of github needs to be checked with
    # a regex and can't simply be passed as a string here
    def __init__(self, path: str):
        self._git_repo = Repo(path=path, search_parent_directories=True)
        # TODO: write function that get's the correct remote based on url
        self._remote = self._git_repo.remote()

    @property
    def git_repo(self) -> Repo:
        return self._git_repo

    @property
    def remote(self) -> Remote:
        return self._remote

    @property
    def root(self) -> str:
        assert self.git_repo.working_dir
        return str(self.git_repo.working_dir)

    @property
    def is_dirty(self) -> bool:
        return self.git_repo.is_dirty(untracked_files=True)

    @property
    def has_local_changes(self) -> bool:
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
        return cast(str, self.git_repo.head.object.hexsha)


class GitHubCodeRepository(BaseCodeRepository):
    def __init__(self, owner: str, repository: str, token: str):
        self._owner = owner
        self._repository = repository
        self._token = token

    def get_local_repo(path: str) -> LocalRepository:
        # TODO: correctly initialize the local git repo, catch potential errors
        try:
            return LocalGitRepository(path=path)
        except ...:
            return None

    def check_remote_url(self, url: str) -> bool:
        https_url = f"https://github.com/{self._owner}/{self._repository}.git"
        if url == https_url:
            return True

        ssh_regex = re.compile(
            f".*@github.com:{self._owner}/{self._repository}.git"
        )
        if ssh_regex.fullmatch(url):
            return True

        return False
