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
import inspect
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type, cast

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact

from zenml.artifacts.type_registry import type_registry
from zenml.exceptions import MaterializerInterfaceError
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)


class BaseMaterializerMeta(type):
    """Metaclass responsible for registering different BaseMaterializer
    subclasses for reading/writing artifacts."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseMaterializerMeta":
        """Creates a Materializer class and registers it at
        the `MaterializerRegistry`."""
        cls = cast(
            Type["BaseMaterializer"], super().__new__(mcs, name, bases, dct)
        )
        if name != "BaseMaterializer":
            from zenml.artifacts.base_artifact import BaseArtifact

            if not cls.ASSOCIATED_TYPES:
                raise MaterializerInterfaceError(
                    f"Invalid materializer class '{name}'. When creating a "
                    f"custom materializer, make sure to specify at least one "
                    f"type in its ASSOCIATED_TYPES class variable.",
                    url="https://docs.zenml.io/guides/index/custom-materializer",
                )

            for artifact_type in cls.ASSOCIATED_ARTIFACT_TYPES:
                if not (
                    inspect.isclass(artifact_type)
                    and issubclass(artifact_type, BaseArtifact)
                ):
                    raise MaterializerInterfaceError(
                        f"Associated artifact type {artifact_type} for "
                        f"materializer {name} is not a `BaseArtifact` "
                        f"subclass.",
                        url="https://docs.zenml.io/guides/index/custom-materializer",
                    )

            artifact_types = cls.ASSOCIATED_ARTIFACT_TYPES or (BaseArtifact,)
            for associated_type in cls.ASSOCIATED_TYPES:
                if not inspect.isclass(associated_type):
                    raise MaterializerInterfaceError(
                        f"Associated type {associated_type} for materializer "
                        f"{name} is not a class.",
                        url="https://docs.zenml.io/guides/index/custom-materializer",
                    )

                default_materializer_registry.register_materializer_type(
                    associated_type, cls
                )

                type_registry.register_integration(
                    associated_type, artifact_types
                )
        return cls


class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_ARTIFACT_TYPES: ClassVar[Tuple[Type["BaseArtifact"], ...]] = ()
    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = ()

    def __init__(self, artifact: "BaseArtifact"):
        """Initializes a materializer with the given artifact."""
        self.artifact = artifact

    def _can_handle_type(self, data_type: Type[Any]) -> bool:
        """Whether the materializer can read/write a certain type."""
        return any(
            issubclass(data_type, associated_type)
            for associated_type in self.ASSOCIATED_TYPES
        )

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Write logic here to handle input of the step function.

        Args:
            data_type: What type the input should be materialized as.
        Returns:
            Any object that is to be passed into the relevant artifact in the
            step.
        """
        if not self._can_handle_type(data_type):
            raise TypeError(
                f"Unable to handle type {data_type}. {self.__class__.__name__} "
                f"can only read artifacts to the following types: "
                f"{self.ASSOCIATED_TYPES}."
            )

    def handle_return(self, data: Any) -> None:
        """Write logic here to handle return of the step function.

        Args:
            data: Any object that is specified as an input artifact of the step.
        """
        data_type = type(data)
        if not self._can_handle_type(data_type):
            raise TypeError(
                f"Unable to write {data_type}. {self.__class__.__name__} "
                f"can only write the following types: {self.ASSOCIATED_TYPES}."
            )
