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

from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Tuple, Type, cast

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact
from zenml.artifacts.type_registry import type_registry
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
            assert cls.ASSOCIATED_TYPES, (
                "You should specify a list of ASSOCIATED_TYPES when creating a "
                "Materializer!"
            )
            for associated_type in cls.ASSOCIATED_TYPES:
                default_materializer_registry.register_materializer_type(
                    associated_type, cls
                )

                if cls.ASSOCIATED_ARTIFACT_TYPES:
                    type_registry.register_integration(
                        associated_type, cls.ASSOCIATED_ARTIFACT_TYPES
                    )
                else:
                    from zenml.artifacts.base_artifact import BaseArtifact

                    type_registry.register_integration(
                        associated_type, [BaseArtifact]
                    )
        return cls


class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_ARTIFACT_TYPES: ClassVar[List[Type["BaseArtifact"]]] = []
    ASSOCIATED_TYPES: ClassVar[List[Type[Any]]] = []

    def __init__(self, artifact: "BaseArtifact"):
        """Initializes a materializer with the given artifact."""
        self.artifact = artifact

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Write logic here to handle input of the step function.

        Args:
            data_type: What type the input should be materialized as.
        Returns:
            Any object that is to be passed into the relevant artifact in the
            step.
        """
        # TODO [ENG-140]: Add type checking for materializer handle_input
        # if data_type not in self.ASSOCIATED_TYPES:
        #     raise ValueError(
        #         f"Data type {data_type} not supported by materializer "
        #         f"{self.__name__}. Supported types: {self.ASSOCIATED_TYPES}"
        #     )

    def handle_return(self, data: Any) -> None:
        """Write logic here to handle return of the step function.

        Args:
            Any object that is specified as an input artifact of the step.
        """
        # TODO [ENG-141]: Put proper type checking
        # if data_type not in self.ASSOCIATED_TYPES:
        #     raise ValueError(
        #         f"Data type {data_type} not supported by materializer "
        #         f"{self.__class__.__name__}. Supported types: "
        #         f"{self.ASSOCIATED_TYPES}"
        #     )
