#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Metaclass implementation for registering ZenML BaseMaterializer subclasses."""

import inspect
from typing import Any, ClassVar, Dict, Optional, Tuple, Type, cast

from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
from zenml.enums import ArtifactType, VisualizationType
from zenml.exceptions import MaterializerInterfaceError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.materializer_registry import materializer_registry
from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)


class BaseMaterializerMeta(type):
    """Metaclass responsible for registering different BaseMaterializer subclasses.

    Materializers are used for reading/writing artifacts.
    """

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseMaterializerMeta":
        """Creates a Materializer class and registers it at the `MaterializerRegistry`.

        Args:
            name: The name of the class.
            bases: The base classes of the class.
            dct: The dictionary of the class.

        Returns:
            The BaseMaterializerMeta class.

        Raises:
            MaterializerInterfaceError: If the class was improperly defined.
        """
        cls = cast(
            Type["BaseMaterializer"], super().__new__(mcs, name, bases, dct)
        )
        if not cls._DOCS_BUILDING_MODE:
            # Skip the following validation and registration for base classes.
            if cls.SKIP_REGISTRATION:
                # Reset the flag so subclasses don't have it set automatically.
                cls.SKIP_REGISTRATION = False
                return cls

            # Validate that the class is properly defined.
            if not cls.ASSOCIATED_TYPES:
                raise MaterializerInterfaceError(
                    f"Invalid materializer class '{name}'. When creating a "
                    f"custom materializer, make sure to specify at least one "
                    f"type in its ASSOCIATED_TYPES class variable.",
                    url="https://docs.zenml.io/how-to/handle-data-artifacts/handle-custom-data-types",
                )

            # Validate associated artifact type.
            if cls.ASSOCIATED_ARTIFACT_TYPE:
                try:
                    cls.ASSOCIATED_ARTIFACT_TYPE = ArtifactType(
                        cls.ASSOCIATED_ARTIFACT_TYPE
                    )
                except ValueError:
                    raise MaterializerInterfaceError(
                        f"Invalid materializer class '{name}'. When creating a "
                        f"custom materializer, make sure to specify a valid "
                        f"artifact type in its ASSOCIATED_ARTIFACT_TYPE class "
                        f"variable.",
                        url="https://docs.zenml.io/how-to/handle-data-artifacts/handle-custom-data-types",
                    )

            # Validate associated data types.
            for associated_type in cls.ASSOCIATED_TYPES:
                if not inspect.isclass(associated_type):
                    raise MaterializerInterfaceError(
                        f"Associated type {associated_type} for materializer "
                        f"{name} is not a class.",
                        url="https://docs.zenml.io/how-to/handle-data-artifacts/handle-custom-data-types",
                    )

            # Register the materializer.
            for associated_type in cls.ASSOCIATED_TYPES:
                materializer_registry.register_materializer_type(
                    associated_type, cls
                )

            from zenml.utils import notebook_utils

            notebook_utils.try_to_save_notebook_cell_code(cls)

        return cls


class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.BASE
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = ()

    # `SKIP_REGISTRATION` can be set to True to not register the class in the
    # materializer registry. This is primarily useful for defining base classes.
    # Subclasses will automatically have this set to False unless they override
    # it themselves.
    SKIP_REGISTRATION: ClassVar[bool] = True

    _DOCS_BUILDING_MODE: ClassVar[bool] = False

    def __init__(
        self, uri: str, artifact_store: Optional[BaseArtifactStore] = None
    ):
        """Initializes a materializer with the given URI.

        Args:
            uri: The URI where the artifact data will be stored.
            artifact_store: The artifact store used to store this artifact.
        """
        self.uri = uri
        self._artifact_store = artifact_store

    @property
    def artifact_store(self) -> BaseArtifactStore:
        """Returns the artifact store used to store this artifact.

        It either comes from the configuration of the materializer or from the
        active stack.

        Returns:
            The artifact store used to store this artifact.
        """
        if self._artifact_store:
            return self._artifact_store
        else:
            from zenml.client import Client

            return Client().active_stack.artifact_store

    # ================
    # Public Interface
    # ================

    def load(self, data_type: Type[Any]) -> Any:
        """Write logic here to load the data of an artifact.

        Args:
            data_type: What type the artifact data should be loaded as.

        Returns:
            The data of the artifact.
        """
        # read from a location inside self.uri
        return None

    def save(self, data: Any) -> None:
        """Write logic here to save the data of an artifact.

        Args:
            data: The data of the artifact to save.
        """
        # write `data` into self.uri

    def save_visualizations(self, data: Any) -> Dict[str, VisualizationType]:
        """Save visualizations of the given data.

        If this method is not overridden, no visualizations will be saved.

        When overriding this method, make sure to save all visualizations to
        files within `self.uri`.

        Example:
        ```
        visualization_uri = os.path.join(self.uri, "visualization.html")
        with self.artifact_store.open(visualization_uri, "w") as f:
            f.write("<html><body>data</body></html>")

        visualization_uri_2 = os.path.join(self.uri, "visualization.png")
        data.save_as_png(visualization_uri_2)

        return {
            visualization_uri: ArtifactVisualizationType.HTML,
            visualization_uri_2: ArtifactVisualizationType.IMAGE
        }
        ```

        Args:
            data: The data of the artifact to visualize.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        # Optionally, save some visualizations of `data` inside `self.uri`.
        return {}

    def extract_metadata(self, data: Any) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given data.

        This metadata will be tracked and displayed alongside the artifact.

        Example:
        ```
        return {
            "some_attribute_i_want_to_track": self.some_attribute,
            "pi": 3.14,
        }
        ```

        Args:
            data: The data to extract metadata from.

        Returns:
            A dictionary of metadata.
        """
        # Optionally, extract some metadata from `data` for ZenML to store.
        return {}

    # ================
    # Internal Methods
    # ================
    def validate_save_type_compatibility(self, data_type: Type[Any]) -> None:
        """Checks whether the materializer can save the given type.

        Args:
            data_type: The type to check.

        Raises:
            TypeError: If the materializer cannot save the given type.
        """
        if not self.can_save_type(data_type):
            raise TypeError(
                f"Unable to save type {data_type}. {self.__class__.__name__} "
                f"can only save artifacts of the following types: "
                f"{self.ASSOCIATED_TYPES}."
            )

    def validate_load_type_compatibility(self, data_type: Type[Any]) -> None:
        """Checks whether the materializer can load the given type.

        Args:
            data_type: The type to check.

        Raises:
            TypeError: If the materializer cannot load the given type.
        """
        if not self.can_load_type(data_type):
            raise TypeError(
                f"Unable to load type {data_type}. {self.__class__.__name__} "
                f"can only load artifacts of the following types: "
                f"{self.ASSOCIATED_TYPES}."
            )

    @classmethod
    def can_save_type(cls, data_type: Type[Any]) -> bool:
        """Whether the materializer can save a certain type.

        Args:
            data_type: The type to check.

        Returns:
            Whether the materializer can save the given type.
        """
        return any(
            issubclass(data_type, associated_type)
            for associated_type in cls.ASSOCIATED_TYPES
        )

    @classmethod
    def can_load_type(cls, data_type: Type[Any]) -> bool:
        """Whether the materializer can load an artifact as the given type.

        Args:
            data_type: The type to check.

        Returns:
            Whether the materializer can load an artifact as the given type.
        """
        return any(
            issubclass(associated_type, data_type)
            for associated_type in cls.ASSOCIATED_TYPES
        )

    def extract_full_metadata(self, data: Any) -> Dict[str, "MetadataType"]:
        """Extract both base and custom metadata from the given data.

        Args:
            data: The data to extract metadata from.

        Returns:
            A dictionary of metadata.
        """
        base_metadata = self._extract_base_metadata(data)
        custom_metadata = self.extract_metadata(data)
        return {**base_metadata, **custom_metadata}

    def _extract_base_metadata(self, data: Any) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given data.

        This metadata will be extracted for all artifacts in addition to the
        metadata extracted by the `extract_metadata` method.

        Args:
            data: The data to extract metadata from.

        Returns:
            A dictionary of metadata.
        """
        from zenml.metadata.metadata_types import StorageSize

        storage_size = fileio.size(self.uri)
        if isinstance(storage_size, int):
            return {"storage_size": StorageSize(storage_size)}
        return {}
