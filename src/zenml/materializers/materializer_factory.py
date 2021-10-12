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

from typing import TYPE_CHECKING, ClassVar, Dict, Type

if TYPE_CHECKING:
    from zenml.artifacts.base_artifact import BaseArtifact
    from zenml.materializers.base_materializer import BaseMaterializer


class MaterializerFactory(object):
    """A factory class which is used by the ZenML artifacts to keep track
    of different materializers"""

    materializer_types: ClassVar[Dict[str, Type["BaseMaterializer"]]] = {}

    def __init__(self, artifact: "BaseArtifact"):
        """Initialization with an empty factory"""
        self.artifact = artifact

    def __getattr__(self, key: str) -> "BaseMaterializer":
        """Get a single materializers based on the key.

        Args:
            key: Indicates the materializer name

        Returns:
            Instance of a `BaseMaterializer` subclass initialized
            with the artifact of this factory.

        Raises
            AttributeError: If no materializer was registered for
                the given key.
        """
        if key in self.materializer_types:
            return self.materializer_types[key](self.artifact)
        else:
            raise AttributeError(
                f"No materializer registered for key `{key}`."
            )

    def get_types(self) -> Dict[str, Type["BaseMaterializer"]]:
        """Get all registered materializers."""
        return self.materializer_types

    @classmethod
    def register_type(cls, key: str, type_: Type["BaseMaterializer"]) -> None:
        """Registers a new materializer.

        Args:
            key: Name with which the materializer can be accessed.
            type_: A BaseMaterializer subclass.
        """
        cls.materializer_types[key] = type_
