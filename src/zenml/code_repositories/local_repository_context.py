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
"""Base class for local code repository contexts."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.code_repositories import BaseCodeRepository

logger = get_logger(__name__)


class LocalRepositoryContext(ABC):
    """Base class for local repository contexts.

    This class is used to represent a local repository. It is used
    to track the current state of the repository and to provide
    information about the repository, such as the root path, the current
    commit, and whether the repository is dirty.
    """

    def __init__(self, code_repository: "BaseCodeRepository") -> None:
        """Initializes a local repository context.

        Args:
            code_repository: The code repository.
        """
        self._code_repository = code_repository

    @property
    def code_repository(self) -> "BaseCodeRepository":
        """Returns the code repository.

        Returns:
            The code repository.
        """
        return self._code_repository

    @property
    @abstractmethod
    def root(self) -> str:
        """Returns the root path of the local repository.

        Returns:
            The root path of the local repository.
        """
        pass

    @property
    @abstractmethod
    def is_dirty(self) -> bool:
        """Returns whether the local repository is dirty.

        A repository counts as dirty if it has any untracked or uncommitted
        changes.

        Returns:
            Whether the local repository is dirty.
        """
        pass

    @property
    @abstractmethod
    def has_local_changes(self) -> bool:
        """Returns whether the local repository has local changes.

        A repository has local changes if it is dirty or there are some commits
        which have not been pushed yet.

        Returns:
            Whether the local repository has local changes.
        """
        pass

    @property
    @abstractmethod
    def current_commit(self) -> str:
        """Returns the current commit of the local repository.

        Returns:
            The current commit of the local repository.
        """
        pass
