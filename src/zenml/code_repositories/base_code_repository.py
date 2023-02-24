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
import importlib
import inspect
import os
import re
import site
import sys
from abc import ABC, abstractmethod
from distutils.sysconfig import get_python_lib
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Optional, Type, Union, cast
from uuid import UUID

from git.exc import InvalidGitRepositoryError
from git.repo.base import Repo
from pydantic import BaseModel, validator

from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.logger import get_logger
from zenml.utils import source_utils

logger = get_logger(__name__)


class BaseCodeRepository(BaseModel, ABC):
    @classmethod
    @abstractmethod
    def exists_at_path(cls, path: str, config: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def login(self) -> None:
        pass

    @abstractmethod
    def is_active(self, path: str) -> bool:
        # whether path is inside the locally checked out repo
        pass

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

    @abstractmethod
    def download_files(self, commit: str, directory: str) -> None:
        # download files of commit to local directory
        pass


class _GitCodeRepository(BaseCodeRepository, ABC):
    @property
    def git_repo(self) -> Repo:
        return Repo(search_parent_directories=True)

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

        remote = self.git_repo.remote(name="origin")  # make this configurable?
        remote.fetch()

        local_commit = self.git_repo.head.commit
        remote_commit = remote.refs[self.git_repo.active_branch].commit

        return remote_commit != local_commit

    @property
    def current_commit(self) -> str:
        return cast(str, self.git_repo.head.object.hexsha)

    @classmethod
    def exists_at_path(cls, path: str, config: Dict[str, Any]) -> bool:
        try:
            repo = Repo(path=path, search_parent_directories=True)
        except InvalidGitRepositoryError:
            return False

        for remote in repo.remotes:
            if cls.url_matches_config(url=remote.url, config=config):
                return True

        return False

    @classmethod
    @abstractmethod
    def url_matches_config(cls, url: str, config: Dict[str, Any]) -> bool:
        pass


class GitHubCodeRepository(_GitCodeRepository):
    def login(self) -> None:
        ...

    def download_files(self, commit: str, directory: str) -> None:
        ...

    @classmethod
    def url_matches_config(cls, url: str, config: Dict[str, Any]) -> bool:
        owner = config["owner"]
        repository = config["repository"]

        https_url = f"https://github.com/{owner}/{repository}.git"
        if url == https_url:
            return True

        ssh_regex = re.compile(f".*@github.com:{owner}/{repository}.git")

        if ssh_regex.fullmatch(url):
            return True

        return False


class SourceType(Enum):
    USER = "user"
    BUILTIN = "builtin"  # TODO: maybe store python version?
    DISTRIBUTION_PACKAGE = "distribution_package"
    CODE_REPOSITORY = "code_repository"
    HUB = "hub"
    UNKNOWN = "unknown"


class Source(BaseModel):
    module: str
    variable: str
    type: SourceType

    def __new__(cls, **kwargs):
        if kwargs.get("type") == SourceType.CODE_REPOSITORY:
            return object.__new__(CodeRepositorySource)
        elif kwargs.get("type") == SourceType.DISTRIBUTION_PACKAGE:
            return object.__new__(DistributionPackageSource)

        return super().__new__(cls)

    @classmethod
    def from_import_path(cls, import_path: str):
        module, variable = import_path.rsplit(".", maxsplit=1)
        return cls(module=module, variable=variable, type=SourceType.UNKNOWN)

    @property
    def import_path(self) -> str:
        return f"{self.module}.{self.variable}"


class DistributionPackageSource(Source):
    version: Optional[str] = None
    type: SourceType = SourceType.DISTRIBUTION_PACKAGE

    @validator("type")
    def _validate_type(cls, value: SourceType) -> SourceType:
        if value != SourceType.DISTRIBUTION_PACKAGE:
            raise ValueError("Invalid source type.")

        return value

    @property
    def package_name(self) -> str:
        # TODO: are dots allowed in package names? If yes we need to handle that
        return self.module.split(".", maxsplit=1)[0]


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
    _SOURCE_MAPPING: Dict[int, Source] = {}

    def load_source(self, source: Union[Source, str]) -> Any:
        if isinstance(source, str):
            source = Source.from_import_path(source)

        import_root = None
        if isinstance(source, CodeRepositorySource):
            import_root = self._load_repository_files(source=source)
        elif isinstance(source, DistributionPackageSource):
            if source.version:
                current_package_version = self._get_package_version(
                    package_name=source.package_name
                )
                if current_package_version != source.version:
                    logger.warning("Package version doesn't match source.")
        elif source.type in {SourceType.USER, SourceType.UNKNOWN}:
            # Unknown source might also refer to a user file, include source
            # root in python path just to be sure
            import_root = self.get_source_root()

        python_path_prefix = [import_root] if import_root else []
        with source_utils.prepend_python_path(python_path_prefix):
            module = importlib.import_module(source.module)
            object_ = getattr(module, source.variable)

        self._SOURCE_MAPPING[id(object_)] = source
        return object_

    def resolve_class(self, class_: Type[Any]) -> Source:
        if id(class_) in self._SOURCE_MAPPING:
            return self._SOURCE_MAPPING[id(class_)]

        module = sys.modules[class_.__module__]

        if not getattr(module, class_.__name__, None) is class_:
            raise RuntimeError(
                "Unable to resolve class, must be top level in module"
            )

        module_name = class_.__module__
        if module_name == "__main__":
            module_name = self._resolve_module(module)

        source_type = self.get_source_type(module=module)

        if source_type == SourceType.USER:
            # TODO: maybe we want to check for a repo at the location of
            # the actual module file here? Different steps could be in
            # different code repos
            source_root = self.get_source_root()
            active_repo = Client().find_active_code_repository(
                path=source_root
            )

            if active_repo and not active_repo.has_local_changes:
                # Inside a clean code repo with all changes pushed, resolve to
                # a code repository source
                module_name = self._resolve_module(
                    module, root=active_repo.root
                )

                return CodeRepositorySource(
                    repository_id=active_repo.id,
                    commit=active_repo.current_commit,
                    module=module_name,
                    variable=class_.__name__,
                )
            else:
                module_name = self._resolve_module(module)
        elif source_type == SourceType.DISTRIBUTION_PACKAGE:
            package_name = module_name.split(".", maxsplit=1)[0]
            package_version = self._get_package_version(
                package_name=package_name
            )
            return DistributionPackageSource(
                module=module_name,
                variable=class_.__name__,
                version=package_version,
                type=source_type,
            )

        return Source(
            module=module_name, variable=class_.__name__, type=source_type
        )

    @staticmethod
    def get_source_root() -> str:
        return source_utils.get_source_root_path()

    @classmethod
    def is_user_file(cls, file_path: str) -> bool:
        source_root = SourceResolver.get_source_root()
        return Path(source_root) in Path(file_path).resolve().parents

    @classmethod
    def is_standard_lib_file(cls, file_path: str) -> bool:
        stdlib_root = get_python_lib(standard_lib=True)
        return Path(stdlib_root).resolve() in Path(file_path).resolve().parents

    @classmethod
    def is_distribution_package_file(cls, file_path: str) -> bool:
        absolute_file_path = Path(file_path).resolve()

        for path in site.getsitepackages() + [site.getusersitepackages()]:
            if Path(path).resolve() in absolute_file_path.parents:
                return True

        # TODO: This currently returns False for editable installs because
        # the site packages dir only contains a reference to the source files,
        # not the actual files. This means editable installs will get source
        # type unknown, which seems reasonable but we need to check if this
        # leads to some issues
        return False

    @classmethod
    def get_source_type(cls, module: ModuleType) -> SourceType:
        try:
            file_path = inspect.getfile(module)
        except (TypeError, OSError):
            # builtin file
            return SourceType.BUILTIN

        if cls.is_standard_lib_file(file_path=file_path):
            return SourceType.BUILTIN

        if cls.is_user_file(file_path=file_path):
            return SourceType.USER

        if cls.is_distribution_package_file(file_path=file_path):
            return SourceType.DISTRIBUTION_PACKAGE

        return SourceType.UNKNOWN

    def _load_repository_files(self, source: CodeRepositorySource) -> str:
        source_root = self.get_source_root()
        active_repo = Client().find_active_code_repository(path=source_root)

        if (
            active_repo
            and active_repo.id == source.repository_id
            and not active_repo.is_dirty
            and active_repo.current_commit == source.commit
        ):
            # The repo is clean and at the correct commit, we can use the file
            # directly without downloading anything
            repo_root = active_repo.root
        else:
            repo_root = os.path.join(
                GlobalConfiguration().config_directory,
                "code_repositories",
                str(source.repository_id),
                source.commit,
            )
            if not os.path.exists(repo_root):
                # TODO: download repo files
                # Client().get_code_repository(source.repository_id)
                ...

        return repo_root

    @classmethod
    def _resolve_module(
        cls, module: ModuleType, custom_source_root: Optional[str] = None
    ) -> str:
        if not hasattr(module, "__file__") or not module.__file__:
            if module.__name__ == "__main__":
                raise RuntimeError(
                    f"{module} module was not loaded from a file. Cannot "
                    "determine the module root path."
                )
            return module.__name__

        module_path = os.path.abspath(module.__file__)

        root = custom_source_root or cls.get_source_root()
        root = os.path.abspath(root)

        # Remove root_path from module_path to get relative path left over
        module_path = os.path.relpath(module_path, root)

        if module_path.startswith(os.pardir):
            raise RuntimeError(
                f"Unable to resolve source for module {module}. The module file "
                f"'{module_path}' does not seem to be inside the source root "
                f"'{root}'."
            )

        # Remove the file extension and replace the os specific path separators
        # with `.` to get the module source
        module_path, file_extension = os.path.splitext(module_path)
        if file_extension != ".py":
            raise RuntimeError(
                f"Unable to resolve source for module {module}. The module file "
                f"'{module_path}' does not seem to be a python file."
            )

        module_source = module_path.replace(os.path.sep, ".")

        logger.debug(
            f"Resolved module source for module {module} to: `{module_source}`"
        )

        return module_source

    @staticmethod
    def _get_package_version(package_name: str) -> Optional[str]:
        # TODO: this only works on python 3.8+
        # TODO: catch errors
        from importlib.metadata import version

        return version(distribution_name=package_name)
