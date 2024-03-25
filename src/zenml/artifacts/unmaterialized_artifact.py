#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Unmaterialized artifact class."""

from zenml.models import ArtifactVersionResponse


class UnmaterializedArtifact(ArtifactVersionResponse):
    """Unmaterialized artifact class.

    Typing a step input to have this type will cause ZenML to not materialize
    the artifact. This is useful for steps that need to access the artifact
    metadata instead of the actual artifact data.

    Usage example:

    ```python
    from zenml import step
    from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact

    @step
    def my_step(input_artifact: UnmaterializedArtifact):
        print(input_artifact.uri)
    ```
    """


UnmaterializedArtifact.model_rebuild()
