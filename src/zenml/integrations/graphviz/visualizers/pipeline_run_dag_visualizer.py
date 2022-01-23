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

import tempfile
from abc import abstractmethod
from typing import Any

import graphviz

from zenml.logger import get_logger
from zenml.post_execution import PipelineRunView
from zenml.visualizers import BasePipelineRunVisualizer

logger = get_logger(__name__)

# TODO [ENG-220]: This integration is working but not really doing much. We
#  should use graphviz to show the pipeline perhaps (not the run).


class PipelineRunDagVisualizer(BasePipelineRunVisualizer):
    """Visualize the lineage of runs in a pipeline."""

    ARTIFACT_DEFAULT_COLOR = "blue"
    ARTIFACT_CACHED_COLOR = "green"
    ARTIFACT_SHAPE = "box"
    ARTIFACT_PREFIX = "artifact_"
    STEP_COLOR = "#431D93"
    STEP_SHAPE = "ellipse"
    STEP_PREFIX = "step_"
    FONT = "Roboto"

    @abstractmethod
    def visualize(
        self, object: PipelineRunView, *args: Any, **kwargs: Any
    ) -> graphviz.Digraph:
        """Creates a pipeline lineage diagram using graphviz."""
        logger.warning(
            "This integration is not completed yet. Results might be unexpected."
        )

        dot = graphviz.Digraph(comment=object.name)

        # link the steps together
        for step in object.steps:
            # add each step as a node
            dot.node(
                self.STEP_PREFIX + str(step.id),
                step.entrypoint_name,
                shape=self.STEP_SHAPE,
            )
            # for each parent of a step, add an edge

            for artifact_name, artifact in step.outputs.items():
                dot.node(
                    self.ARTIFACT_PREFIX + str(artifact.id),
                    f"{artifact_name} \n" f"({artifact._data_type})",
                    shape=self.ARTIFACT_SHAPE,
                )
                dot.edge(
                    self.STEP_PREFIX + str(step.id),
                    self.ARTIFACT_PREFIX + str(artifact.id),
                )

            for artifact_name, artifact in step.inputs.items():
                dot.edge(
                    self.ARTIFACT_PREFIX + str(artifact.id),
                    self.STEP_PREFIX + str(step.id),
                )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
            dot.render(filename=f.name, format="png", view=True, cleanup=True)
        return dot
