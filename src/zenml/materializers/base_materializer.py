#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from typing import TYPE_CHECKING, Any, Type

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact

from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)


class BaseMaterializerMeta(type):
    """Metaclass responsible for registering different BaseMaterializer
    subclasses for reading/writing artifacts."""

    def __new__(mcs, name, bases, dct):
        """Creates a Materializer class and registers it at
        the `MaterializerFactory`."""
        cls = super().__new__(mcs, name, bases, dct)
        if name != "BaseMaterializer":
            assert cls.ASSOCIATED_TYPES is not None, (  # noqa
                "You should specify a list of ASSOCIATED_TYPES when creating a "
                "Materializer!"
            )
            [
                default_materializer_registry.register_materializer_type(x, cls)
                for x in cls.ASSOCIATED_TYPES  # noqa
            ]  # noqa
        return cls


class BaseMaterializer(metaclass=BaseMaterializerMeta):
    """Base Materializer to realize artifact data."""

    ASSOCIATED_TYPES = None

    def __init__(self, artifact: "BaseArtifact"):
        """Initializes a materializer with the given artifact."""
        self.artifact = artifact

    def handle_input(self, data_type: Type) -> Any:
        """Write logic here to handle input of the step function.

        Args:
            data_type: What type the input should be materialized as.
        Returns:
            Any object that is to be passed into the relevant artifact in the
            step.
        """
        # TODO [MEDIUM]: Type checking
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
        # TODO [MEDIUM]: Put proper type checking
        # if data_type not in self.ASSOCIATED_TYPES:
        #     raise ValueError(
        #         f"Data type {data_type} not supported by materializer "
        #         f"{self.__class__.__name__}. Supported types: "
        #         f"{self.ASSOCIATED_TYPES}"
        #     )
