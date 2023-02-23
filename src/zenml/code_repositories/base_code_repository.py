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
import inspect
import os
import sys
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel, validator

from zenml.config.global_config import GlobalConfiguration
from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)


def find_active_code_repo(path: str) -> Optional["BaseCodeRepository"]:
    # find if we have a registered (authenticated?) code repo that exists
    # at that path
    return None


class BaseCodeRepository(BaseModel, ABC):
    id: UUID

    @abstractmethod
    def login(self) -> None:
        pass

    @abstractmethod
    def is_active(self, path: str) -> bool:
        # whether path is inside the locally checked out repo
        pass

    @abstractmethod
    def get_root(self, path: str) -> str:
        # get repo root
        pass

    @abstractmethod
    def get_relative_file_path(self, path: str) -> str:
        # get path of file relative to repo root
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

    @abstractmethod
    def download_files(self, commit: str, directory: str) -> None:
        # download files of commit to local directory
        pass

    @classmethod
    @abstractmethod
    def is_valid_repo(cls, path: str) -> bool:
        # check if the path is a repo of this type (e.g. git repo), maybe
        # return some information that we can use to fetch a potentially
        # registered code repo from the client
        pass


class _GitCodeRepository(BaseCodeRepository, ABC):
    ...


class GitHubCodeRepository(_GitCodeRepository):
    ...


class SourceType(Enum):
    USER = "user"
    BUILTIN = "builtin"
    SITE_PACKAGE = "site_package"  # maybe rename and add python stdlib?
    CODE_REPOSITORY = "code_repository"
    UNKNOWN = "unknown"


class Source(BaseModel):
    module: str
    variable: str
    type: SourceType

    def __new__(cls, **kwargs):
        if kwargs.get("type") == SourceType.CODE_REPOSITORY:
            return object.__new__(CodeRepositorySource)
        return super().__new__(cls)


class CodeRepositorySource(Source):
    repository_id: UUID
    commit: str
    type: SourceType = SourceType.CODE_REPOSITORY

    @validator("type")
    def _validate_type(cls, value: SourceType) -> SourceType:
        if value != SourceType.CODE_REPOSITORY:
            raise ValueError("Invalid source type.")

        return value


class SourceResolver:
    SOURCE_MAPPING: Dict[int, Source] = {}

    @staticmethod
    def get_source_root() -> str:
        return source_utils.get_source_root_path()

    @classmethod
    def is_user_file(cls, file_path: str) -> bool:
        source_root = SourceResolver.get_source_root()
        return Path(source_root) in Path(file_path).resolve().parents

    @classmethod
    def get_source_type(cls, module: ModuleType) -> SourceType:
        try:
            file_path = inspect.getfile(module)
        except (TypeError, OSError):
            return SourceType.BUILTIN

        if cls.is_user_file(file_path=file_path):
            return SourceType.USER

        if source_utils.is_third_party_module(file_path=file_path):
            return SourceType.SITE_PACKAGE

        return SourceType.UNKNOWN

    def load_source(self, source: Union[Source, str]) -> Any:
        if isinstance(source, str):
            # str source for backwards compatability
            module, variable = source.rsplit(".", maxsplit=1)
            source = Source(
                module=module, variable=variable, type=SourceType.UNKNOWN
            )

        repo_root = None
        if isinstance(source, CodeRepositorySource):
            repo_root = self._load_code_repository(source=source)

        source_path = f"{source.module}.{source.variable}"
        object_ = source_utils.load_source_path(
            source_path, import_path=repo_root
        )

        self.SOURCE_MAPPING[id(object_)] = source
        return object_

    def _load_code_repository(self, source: CodeRepositorySource) -> str:
        source_root = self.get_source_root()
        active_repo = find_active_code_repo(path=source_root)

        if (
            active_repo
            and active_repo.id == source.repository_id
            and not active_repo.is_dirty
            and active_repo.current_commit == source.commit
        ):
            # The repo is clean and at the correct commit, we can use the file
            # directly without downloading anything
            repo_root = active_repo.get_root(path=source_root)
        else:
            repo_root = os.path.join(
                GlobalConfiguration().config_directory,
                "code_repositories",
                str(source.repository_id),
                source.commit,
            )
            if not os.path.exists(repo_root):
                ...

        return repo_root

    def resolve_class(self, class_: Type[Any]) -> Source:
        if id(class_) in self.SOURCE_MAPPING:
            return self.SOURCE_MAPPING[id(class_)]

        module = sys.modules[class_.__module__]

        if not getattr(module, class_.__name__, None) is class_:
            raise RuntimeError(
                "Unable to resolve class, must be top level in module"
            )

        module_name = class_.__module__
        if module_name == "__main__":
            module_name = source_utils.get_main_module_source()

        source_type = self.get_source_type(module=module)

        if source_type == SourceType.USER:
            source_root = self.get_source_root()
            active_repo = find_active_code_repo(path=source_root)

            if active_repo and not active_repo.has_local_changes:
                # Inside a clean code repo with all changes pushed, resolve to
                # a code repository source
                module_path = active_repo.get_relative_file_path(
                    module.__file__
                )
                module_name = module_path.replace(os.path.sep, ".")

                return CodeRepositorySource(
                    repository_id=active_repo.id,
                    commit=active_repo.current_commit,
                    module=module_name,
                    variable=class_.__name__,
                )
            else:
                # Resolve the module relative to the source root
                module_name = source_utils.get_module_source_from_module(
                    module
                )

        return Source(
            module=module_name, variable=class_.__name__, type=source_type
        )
