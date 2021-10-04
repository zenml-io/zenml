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

from abc import abstractmethod

from zenml.artifacts.base_artifact import BaseArtifact


class BaseMaterializer:
    """Base Materializer to realize artifact data."""

    def __init__(self, artifact: BaseArtifact):
        self.artifact = artifact

    @abstractmethod
    def read(self, *args, **kwargs):
        """Base read method to read artifact."""

    @abstractmethod
    def write(self, *args, **kwargs):
        """Base write method to write artifact."""
