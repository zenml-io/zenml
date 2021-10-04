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

from tfx.types import Artifact

from zenml.utils.exceptions import ArtifactInterfaceError


class MaterializerFactory(object):
    """A factory class which is used by the ZenML artifacts to keep track
    of different materializers"""

    def __init__(self, artifact):
        """Initialization with an empty factory"""
        self.types = {}
        self.artifact = artifact

    def __getattr__(self, key):
        """Get a single materializers based on the key

        Args:
            key: str, which indicates the materializer name

        Returns:
            The corresponding writer function within the factory
        """
        if key in self.types:
            return self.types[key](self.artifact)
        else:
            return object.__getattribute__(self, key)(self.artifact)

    def get_types(self):
        """Get the materializer dictionary"""
        return self.types

    def register_type(self, key, type_):
        """Register a new materializer in the factory

        Args:
            key: str, which indicates the materializer used within the step

            type_: a ZenML materializer object
        """
        self.types[key] = type_


class BaseArtifact(Artifact):
    """Base class for all ZenML artifacts.

    Every implementation of an artifact needs to inherit this class.

    While inheriting from this class there are a few things to consider:

    - Upon creation, each artifact class needs to be given a unique TYPE_NAME.
    - Your artifact can feature different properties under the parameter
        PROPERTIES which will be tracked throughout your pipeline runs.
    - TODO [MEDIUM]: Write about the materializers
    """

    TYPE_NAME = "BaseArtifact"
    PROPERTIES = {}

    @property
    def materializers(self) -> MaterializerFactory:
        return MaterializerFactory(self)

    @materializers.setter
    def materializers(self, m):
        raise ArtifactInterfaceError("You cannot set materializers.")
