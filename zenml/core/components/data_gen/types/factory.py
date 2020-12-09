#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

from zenml.core.components.data_gen import constants
from zenml.core.components.data_gen.types.images import ImageConverter
from zenml.core.components.data_gen.types.segmented_images import CVImageConverter
from zenml.core.components.data_gen.types.tabular import TabularConverter
from zenml.core.components.data_gen.types.text import TextConverter


class TypeFactory:

    def __init__(self):
        self.types = {}

    def get_types(self):
        return self.types

    def get_single_type(self, key):
        """
        Args:
            key:
        """
        return self.types[key]

    def register_type(self, key, type_):
        """
        Args:
            key:
            type_:
        """
        self.types[key] = type_


# Register the injections into the factory
type_factory = TypeFactory()
type_factory.register_type(constants.TYPE_TEXT, TextConverter)
type_factory.register_type(constants.TYPE_TABULAR, TabularConverter)
type_factory.register_type(constants.TYPE_IMAGE, ImageConverter)
type_factory.register_type(constants.TYPE_IMAGE_SEG, CVImageConverter)
