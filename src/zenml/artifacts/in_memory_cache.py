#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""In-memory artifact cache."""

import contextvars
from typing import Any, Dict
from uuid import UUID

from zenml.utils import context_utils


class InMemoryArtifactCache(context_utils.BaseContext):
    """In-memory artifact cache."""

    __context_var__ = contextvars.ContextVar("in_memory_artifact_cache")

    def __init__(self) -> None:
        """Initialize the artifact cache."""
        super().__init__()
        self._cache: Dict[UUID, Any] = {}

    def clear(self) -> None:
        """Clear the artifact cache."""
        self._cache = {}

    def get_artifact_data(self, id_: UUID) -> Any:
        """Get the artifact data.

        Args:
            id_: The ID of the artifact to get the data for.

        Returns:
            The artifact data.
        """
        return self._cache.get(id_)

    def set_artifact_data(self, id_: UUID, data: Any) -> None:
        """Set the artifact data.

        Args:
            id_: The ID of the artifact to set the data for.
            data: The artifact data to set.
        """
        self._cache[id_] = data
