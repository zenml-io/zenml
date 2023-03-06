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
from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar
from uuid import UUID

from zenml.logger import get_logger
from zenml.models.code_repository_models import CodeRepositoryResponseModel
from zenml.utils import source_utils_v2

logger = get_logger(__name__)

C = TypeVar("C", bound="BaseCodeRepository")


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
