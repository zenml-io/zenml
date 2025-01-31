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
"""Base class for code repositories."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Set, Type
from uuid import UUID, uuid4

from zenml.config.secret_reference_mixin import SecretReferenceMixin
from zenml.logger import get_logger
from zenml.models import CodeRepositoryResponse
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.code_repositories import LocalRepositoryContext

logger = get_logger(__name__)


class BaseCodeRepositoryConfig(SecretReferenceMixin, ABC):
    """Base config for code repositories."""


class BaseCodeRepository(ABC):
    """Base class for code repositories.

    Code repositories are used to connect to a remote code repository and
    store information about the repository, such as the URL, the owner,
    the repository name, and the host. They also provide methods to
    download files from the repository when a pipeline is run remotely.
    """

    def __init__(
        self,
        id: UUID,
        name: str,
        config: Dict[str, Any],
    ) -> None:
        """Initializes a code repository.

        Args:
            id: The ID of the code repository.
            name: The name of the code repository.
            config: The config of the code repository.
        """
        self._id = id
        self._name = name
        self._config = config
        self.login()

    @property
    def config(self) -> "BaseCodeRepositoryConfig":
        """Config class for Code Repository.

        Returns:
            The config class.
        """
        return BaseCodeRepositoryConfig(**self._config)

    @classmethod
    def from_model(cls, model: CodeRepositoryResponse) -> "BaseCodeRepository":
        """Loads a code repository from a model.

        Args:
            model: The CodeRepositoryResponseModel to load from.

        Returns:
            The loaded code repository object.
        """
        class_: Type[BaseCodeRepository] = (
            source_utils.load_and_validate_class(
                source=model.source, expected_class=BaseCodeRepository
            )
        )
        return class_(id=model.id, name=model.name, config=model.config)

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> None:
        """Validate the code repository config.

        This method should check that the config/credentials are valid and
        the configured repository exists.

        Args:
            config: The configuration.
        """
        # The initialization calls the login to verify the credentials
        code_repo = cls(id=uuid4(), name="", config=config)

        # Explicitly access the config for pydantic validation
        _ = code_repo.config

    @property
    def id(self) -> UUID:
        """ID of the code repository.

        Returns:
            The ID of the code repository.
        """
        return self._id

    @property
    def name(self) -> str:
        """Name of the code repository.

        Returns:
            The name of the code repository.
        """
        return self._name

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
        """Logs into the code repository.

        This method is called when the code repository is initialized.
        It should be used to authenticate with the code repository.

        Raises:
            RuntimeError: If the login fails.
        """
        pass

    @abstractmethod
    def download_files(
        self, commit: str, directory: str, repo_sub_directory: Optional[str]
    ) -> None:
        """Downloads files from the code repository to a local directory.

        Args:
            commit: The commit hash to download files from.
            directory: The directory to download files to.
            repo_sub_directory: The subdirectory in the repository to
                download files from.

        Raises:
            RuntimeError: If the download fails.
        """
        pass

    @abstractmethod
    def get_local_context(
        self, path: str
    ) -> Optional["LocalRepositoryContext"]:
        """Gets a local repository context from a path.

        Args:
            path: The path to the local repository.

        Returns:
            The local repository context object.
        """
        pass
