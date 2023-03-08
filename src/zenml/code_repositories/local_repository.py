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
from typing import TYPE_CHECKING

from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.code_repositories import BaseCodeRepository

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
