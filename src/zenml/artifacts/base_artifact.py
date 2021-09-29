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


class IOFactory:
    """A factory class which is used by the ZenML artifacts to keep track
    of different read/write methods"""

    def __init__(self):
        """Initialization with an empty factory"""
        self.types = {}

    def get_types(self):
        """Get the whole reader/writer dictionary"""
        return self.types

    def get_single_type(self, key):
        """Get a single reader/writer based on the key
        Args:
            key: str, which indicates which type of method will be used within
                the step

        Returns:
            The corresponding writer function within the factory
        """
        return self.types[key]

    def register_type(self, key, type_):
        """Register a new writer in the factory

        Args:
            key: str, which indicates which type of method

            type_: a function which is used to read/write the artifact within
                the context of a step
        """
        self.types[key] = type_


class BaseArtifact(Artifact):
    """Base class for all ZenML artifacts.

    Every implementation of an artifact needs to inherit this class.

    While inheriting from this class there are a few things to consider:

    - Upon creation, each artifact class needs to be given a unique TYPE_NAME.
    - Your artifact can feature different properties under the parameter
        PROPERTIES which will be tracked throughout your pipeline runs.
    - TODO: Write about the reader/writer factories
    """

    TYPE_NAME = "BaseArtifact"
    PROPERTIES = {}

    # Initialize the io factories
    READER_FACTORY = IOFactory()
    WRITER_FACTORY = IOFactory()

    # TODO: Improve the following methods with more checks and error messages
    @classmethod
    def register_reader(cls, key, func):
        cls.READER_FACTORY.register_type(key, func)

    @classmethod
    def register_writer(cls, key, func):
        cls.WRITER_FACTORY.register_type(key, func)

    def get_reader(self, key):
        return self.READER_FACTORY.get_single_type(key)

    def get_writer(self, key):
        return self.WRITER_FACTORY.get_single_type(key)
