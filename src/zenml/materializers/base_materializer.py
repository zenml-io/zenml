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

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.enums import ArtifactType
from zenml.exceptions import MaterializerInterfaceError
from zenml.logger import get_logger
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)

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

        # Skip the following validation and registration for the base class.
        if name == "BaseMaterializer":
            return cls

        # Validate that the class is properly defined.
        if not cls.ASSOCIATED_TYPES:
            raise MaterializerInterfaceError(
                f"Invalid materializer class '{name}'. When creating a "
                f"custom materializer, make sure to specify at least one "
                f"type in its ASSOCIATED_TYPES class variable.",
                url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
            )

        # Check if the deprecated ASSOCIATED_ARTIFACT_TYPES is used.
        artifact_type: str = cls.ASSOCIATED_ARTIFACT_TYPE
        if cls.ASSOCIATED_ARTIFACT_TYPES:
            logger.warning(
                "The `materializer.ASSOCIATED_ARTIFACT_TYPES` class variable "
                "is deprecated and will be removed in a future release. Please "
                f"adjust your '{name}' materializer to use "
                "`ASSOCIATED_ARTIFACT_TYPE` instead."
            )
            artifact_class = cls.ASSOCIATED_ARTIFACT_TYPES[0]
            if not (
                inspect.isclass(artifact_class)
                and issubclass(artifact_class, BaseArtifact)
            ):
                raise MaterializerInterfaceError(
                    f"ASSOCIATED_ARTIFACT_TYPES value '{artifact_class}' for "
                    f"materializer '{name}' is not a `BaseArtifact` "
                    f"subclass.",
                    url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
                )
            artifact_type = artifact_class.TYPE_NAME

        # Validate associated artifact type.
        if artifact_type:
            try:
                cls.ASSOCIATED_ARTIFACT_TYPE = ArtifactType(artifact_type)
            except ValueError:
                raise MaterializerInterfaceError(
                    f"Invalid materializer class '{name}'. When creating a "
                    f"custom materializer, make sure to specify a valid "
                    f"artifact type in its ASSOCIATED_ARTIFACT_TYPE class "
                    f"variable.",
                    url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
                )

        # Validate associated data types.
        for associated_type in cls.ASSOCIATED_TYPES:
            if not inspect.isclass(associated_type):
                raise MaterializerInterfaceError(
                    f"Associated type {associated_type} for materializer "
                    f"{name} is not a class.",
                    url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
                )

        # Register the materializer.
        for associated_type in cls.ASSOCIATED_TYPES:
            default_materializer_registry.register_materializer_type(
                associated_type, cls
            )

        return cls


class DeprecatedArtifact:
    """Mock artifact class to support deprecated `materializer.artifact.uri`."""

    def __init__(self, uri: str) -> None:
        """Initializes the artifact.

        Args:
            uri: The URI of the artifact.
        """
        self._uri = uri

    @property
    def uri(self) -> str:
        """Returns the URI of the artifact.

        Returns:
            The URI of the artifact.
        """
        logger.warning(
            "Calling `materializer.artifact.uri` is deprecated and will be "
            "removed in a future release. Please use `materializer.uri` "
            "instead."
        )
        return self._uri


class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.BASE
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = ()

    # Deprecated; will be removed in a future release.
    ASSOCIATED_ARTIFACT_TYPES: ClassVar[Tuple[Type["BaseArtifact"], ...]] = ()

    def __init__(
        self,
        uri: Optional[str] = None,
        artifact: Optional["BaseArtifact"] = None,
    ):
        """Initializes a materializer with the given URI.

        Args:
            uri: The URI where the artifact data is stored.
            artifact: Deprecated; will be removed in a future release.

        Raises:
            ValueError: If neither a URI nor an artifact is provided.
        """
        if isinstance(uri, BaseArtifact):
            artifact = uri
        if artifact is not None:
            logger.warning(
                "Initializing a materializer with an artifact is deprecated "
                "and will be removed in a future release. Please initialize "
                "the materializer with the artifact's URI instead via "
                "`materializer = MyMaterializer(uri=artifact.uri)`."
            )
            self.uri = artifact.uri
        elif uri is not None:
            self.uri = uri
        else:
            raise ValueError(
                "Initializing a materializer requires either a URI or an "
                "artifact."
            )
        self.artifact = DeprecatedArtifact(self.uri)

    def _can_handle_type(self, data_type: Type[Any]) -> bool:
        """Whether the materializer can read/write a certain type.

        Args:
            data_type: The type to check.

        Returns:
            Whether the materializer can read/write the given type.
        """
        return any(
            issubclass(data_type, associated_type)
            for associated_type in self.ASSOCIATED_TYPES
        )

    def load(self, data_type: Type[Any]) -> Any:
        """Write logic here to load the data of an artifact.

        Args:
            data_type: What type the artifact data should be loaded as.

        Returns:
            The data of the artifact.

        Raises:
            TypeError: If the artifact data is not of the correct type.
        """
        if not self._can_handle_type(data_type):
            raise TypeError(
                f"Unable to handle type {data_type}. {self.__class__.__name__} "
                f"can only read artifacts to the following types: "
                f"{self.ASSOCIATED_TYPES}."
            )

        # If `handle_input` is overridden, call it here to not break custom
        # materializers.
        if type(self).handle_input != BaseMaterializer.handle_input:
            logger.warning(
                "The `materializer.handle_input` method is deprecated and will "
                "be removed in a future release. Please adjust your "
                f"'{type(self).__name__}' materializer to override and use "
                "`materializer.load` instead."
            )
            return self.handle_input(data_type)

        return None

    def save(self, data: Any) -> None:
        """Write logic here to save the data of an artifact.

        Args:
            data: The data of the artifact to save.

        Raises:
            TypeError: If the artifact data is not of the correct type.
        """
        data_type = type(data)
        if not self._can_handle_type(data_type):
            raise TypeError(
                f"Unable to write {data_type}. {self.__class__.__name__} "
                f"can only write the following types: {self.ASSOCIATED_TYPES}."
            )

        # If `handle_return` is overridden, call it here to not break custom
        # materializers.
        if type(self).handle_return != BaseMaterializer.handle_return:
            logger.warning(
                "The `materializer.handle_return` method is deprecated and will "
                "be removed in a future release. Please adjust your "
                f"'{type(self).__name__}' materializer to override and use "
                "`materializer.save` instead."
            )
            self.handle_return(data)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Deprecated method to load the data of an artifact.

        Args:
            data_type: What type the artifact data should be loaded as.

        Returns:
            The data of the artifact.
        """
        logger.warning(
            "The `materializer.handle_input` method is deprecated and will "
            "be removed in a future release. Please use `materializer.load` "
            "instead."
        )

        # If `handle_input` is called on a new materializer that does not
        # override it, call `load` instead.
        if type(self).handle_input == BaseMaterializer.handle_input:
            return self.load(data_type)

    def handle_return(self, data: Any) -> None:
        """Deprecated method to save the data of an artifact.

        Args:
            data: The data of the artifact to save.
        """
        logger.warning(
            "The `materializer.handle_return` method is deprecated and will "
            "be removed in a future release. Please use `materializer.save` "
            "instead."
        )

        # If `handle_return` is called on a new materializer that does not
        # override it, call `save` instead.
        if type(self).handle_return == BaseMaterializer.handle_return:
            self.save(data)
