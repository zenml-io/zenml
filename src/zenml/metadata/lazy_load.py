#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Run Metadata Lazy Loader definition."""

from typing import Optional

from pydantic import BaseModel

from zenml.metadata.metadata_types import MetadataType


class LazyRunMetadataResponse(BaseModel):
    """Lazy run metadata response.

    Used if the run metadata is accessed from the model in
    a pipeline context available only during pipeline compilation.
    """

    lazy_load_artifact_name: Optional[str] = None
    lazy_load_artifact_version: Optional[str] = None
    lazy_load_metadata_name: Optional[str] = None
    lazy_load_model_name: str
    lazy_load_model_version: Optional[str] = None


class RunMetadataLazyGetter:
    """Run Metadata Lazy Getter helper class.

    It serves the purpose to feed back to the user the metadata
    lazy loader wrapper for any given key, if called inside a pipeline
    design time context.
    """

    def __init__(
        self,
        _lazy_load_model_name: str,
        _lazy_load_model_version: Optional[str],
        _lazy_load_artifact_name: Optional[str] = None,
        _lazy_load_artifact_version: Optional[str] = None,
    ):
        """Initialize a RunMetadataLazyGetter.

        Args:
            _lazy_load_model_name: The model name.
            _lazy_load_model_version: The model version.
            _lazy_load_artifact_name: The artifact name.
            _lazy_load_artifact_version: The artifact version.
        """
        self._lazy_load_model_name = _lazy_load_model_name
        self._lazy_load_model_version = _lazy_load_model_version
        self._lazy_load_artifact_name = _lazy_load_artifact_name
        self._lazy_load_artifact_version = _lazy_load_artifact_version

    def __getitem__(self, key: str) -> MetadataType:
        """Get the metadata for the given key.

        Args:
            key: The metadata key.

        Returns:
            The metadata lazy loader wrapper for the given key.
        """
        return LazyRunMetadataResponse(  # type: ignore[return-value]
            lazy_load_model_name=self._lazy_load_model_name,
            lazy_load_model_version=self._lazy_load_model_version,
            lazy_load_artifact_name=self._lazy_load_artifact_name,
            lazy_load_artifact_version=self._lazy_load_artifact_version,
            lazy_load_metadata_name=key,
        )
