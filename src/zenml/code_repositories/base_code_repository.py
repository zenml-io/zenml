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
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Type
from uuid import UUID

from zenml.config.secret_reference_mixin import SecretReferenceMixin
from zenml.logger import get_logger
from zenml.models.code_repository_models import CodeRepositoryResponseModel
from zenml.utils import source_utils_v2

if TYPE_CHECKING:
    from zenml.code_repositories import LocalRepository

logger = get_logger(__name__)


class BaseCodeRepositoryConfig(SecretReferenceMixin, ABC):
    """Base config for code repositories."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class BaseCodeRepository(ABC):
    def __init__(
        self,
        id: UUID,
        config: Dict[str, Any],
    ) -> None:
        self._id = id
        self._config = config
        self.login()

    @property
    def config(self) -> BaseCodeRepositoryConfig:
        """Config class for Code Repository.

        Returns:
            The config class.
        """
        return BaseCodeRepositoryConfig(**self._config)

    @classmethod
    def from_model(
        cls, model: CodeRepositoryResponseModel
    ) -> "BaseCodeRepository":

        class_: Type[
            BaseCodeRepository
        ] = source_utils_v2.load_and_validate_class(
            source=model.source, expected_class=BaseCodeRepository
        )
        return class_(id=model.id, config=model.config)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def requirements(self) -> Set[str]:
        """Set of PyPI requirements for the repository.

        Returns:
            A set of PyPI requirements for the repository.
        """
        from zenml.integrations.utils import get_requirements_for_module

        return set(get_requirements_for_module(self.__module__))

    @abstractmethod
    def login(self) -> None:
        # Validate credentials and login
        pass

    @abstractmethod
    def download_files(
        self, commit: str, directory: str, repo_sub_directory: Optional[str]
    ) -> None:
        # download files of commit to local directory
        pass

    @abstractmethod
    def get_local_repo(self, path: str) -> Optional["LocalRepository"]:
        pass
