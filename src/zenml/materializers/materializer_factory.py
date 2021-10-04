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

from typing import Text


class MaterializerFactory(object):
    """A factory class which is used by the ZenML artifacts to keep track
    of different materializers"""

    materializer_types = {}

    def __init__(self, artifact):
        """Initialization with an empty factory"""
        self.artifact = artifact

    def __getattr__(self, key: Text):
        """Get a single materializers based on the key.

        Args:
            key: Indicates the materializer name

        Returns:
            The corresponding writer function within the factory.
        """
        if key in self.materializer_types:
            return self.materializer_types[key](self.artifact)
        else:
            return object.__getattribute__(self, key)(self.artifact)

    def get_types(self):
        """Get the materializer dictionary"""
        return self.materializer_types

    @classmethod
    def register_type(cls, key, type_):
        """Register a new materializer in the factory

        Args:
            key: str, which indicates the materializer used within the step

            type_: a ZenML materializer object
        """
        cls.materializer_types[key] = type_
