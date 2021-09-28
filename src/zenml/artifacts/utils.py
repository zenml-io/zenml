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


class WriterFactory:
    """A factory class which is used by the ZenML artifacts to keep track
    of different write methods based on the output type"""

    def __init__(self):
        """Initialization with an empty factory"""
        self.types = {}

    def get_types(self):
        """Get the whole writer dictionary"""
        return self.types

    def get_single_type(self, key):
        """Get a single write based on the key
        Args:
          key: an output annotation which indicates which type of output is
            being used by the step

        Returns:
            The corresponding writer function within the factory
        """
        return self.types[key]

    def register_type(self, key, type_):
        """Register a new writer in the factory

        Args:
          key: an output annotation which indicates which type of output is
            being used by the step
          type_: a function which is used to write the returns of the process
            function of the step
        """
        self.types[key] = type_
