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

from zenml.artifacts.utils import WriterFactory


class BaseArtifact(Artifact):
    """Base class for all ZenML artifacts.

    Every implementation of an artifact needs to inherit this class.

    While inheriting from this class there are a few things to consider:

    - Upon creation, each artifact class needs to be given a unique TYPE_NAME.
    - Your artifact can feature different properties under the parameter
        PROPERTIES which will be tracked throughout your pipeline runs.
    - Lastly, each artifact features a writer factory. This factory is used
        to dictate how the artifact needs to be written based on the output
        type within the step definition
    """

    TYPE_NAME = "BaseArtifact"
    PROPERTIES = {}
    WRITER_FACTORY = WriterFactory()

    def get_writer(self, key):
        """ Utility function to have a direct access to the factory """
        return self.WRITER_FACTORY.get_single_type(key)
