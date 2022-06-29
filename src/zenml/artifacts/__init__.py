#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Artifacts are the data that power your experimentation and model training.

It is actually steps that produce artifacts, which are then stored in the
artifact store. Artifacts are written in the signature of a step like so:

```python
    def my_step(first_artifact: int, second_artifact: torch.nn.Module -> int:
        # first_artifact is an integer
        # second_artifact is a torch.nn.Module
        return 1
```
Artifacts can be serialized and deserialized (i.e. written and read from the
Artifact Store) in various ways like ``TFRecords`` or saved model pickles,
depending on what the step produces.The serialization and deserialization logic
of artifacts is defined by the appropriate Materializer.
"""

from zenml.artifacts.data_analysis_artifact import DataAnalysisArtifact
from zenml.artifacts.data_artifact import DataArtifact
from zenml.artifacts.model_artifact import ModelArtifact
from zenml.artifacts.schema_artifact import SchemaArtifact
from zenml.artifacts.service_artifact import ServiceArtifact
from zenml.artifacts.statistics_artifact import StatisticsArtifact

__all__ = [
    "DataAnalysisArtifact",
    "DataArtifact",
    "ModelArtifact",
    "SchemaArtifact",
    "ServiceArtifact",
    "StatisticsArtifact",
]
