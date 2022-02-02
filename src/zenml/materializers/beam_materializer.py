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

from typing import Any, Type

import apache_beam as beam

from zenml.artifacts import DataArtifact
from zenml.materializers.base_materializer import BaseMaterializer


class BeamMaterializer(BaseMaterializer):
    """Materializer to read data to and from beam."""

    ASSOCIATED_TYPES = (beam.PCollection,)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """Reads all files inside the artifact directory and materializes them
        as a beam compatible output."""
        # TODO [ENG-138]: Implement beam reading
        super().handle_input(data_type)

    def handle_return(self, pipeline: beam.Pipeline) -> None:
        """Appends a beam.io.WriteToParquet at the end of a beam pipeline
        and therefore persists the results.

        Args:
            pipeline: A beam.pipeline object.
        """
        # TODO [ENG-139]: Implement beam writing
        super().handle_return(pipeline)
        pipeline | beam.ParDo()
        pipeline.run()
        # pipeline | beam.io.WriteToParquet(self.artifact.uri)
        # pipeline.run()
