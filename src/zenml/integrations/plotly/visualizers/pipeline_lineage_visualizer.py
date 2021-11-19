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
from typing import Any

from zenml.logger import get_logger
from zenml.post_execution.pipeline import PipelineView
from zenml.visualizers.base_pipeline_visualizer import BasePipelineVisualizer

# import pandas as pd
# import plotly.express as px
# from plotly.graph_objs import Figure


logger = get_logger(__name__)


class PipelineLineageVisualizer(BasePipelineVisualizer):
    """Visualize the lineage of runs in a pipeline."""

    @abstractmethod
    def visualize(
        self, object: PipelineView, *args: Any, **kwargs: Any
    ) -> None:
        """Creates a pipeline lineage diagram using plotly.

        Args:
            pipeline:
            *args:
            **kwargs:

        Returns:

        """
        raise NotImplementedError

        # WIP:
        """
        category_df = {}
        dimensions = ["run"]
        for run in pipeline.runs:
            category_df[run.name] = {"run": run.name}
            for step in run.steps:
                # for artifact_name, artifact in step.outputs.items():
                category_df[run.name].update(
                    {
                        step.name: step.id,
                    }
                )
                if step.name not in dimensions:
                    dimensions.append(f"{step.name}")

        category_df = pd.DataFrame.from_dict(category_df, orient="index")

        category_df = category_df.reset_index()

        fig = px.parallel_categories(
            category_df,
            dimensions,
            color=None,
            labels="status",
        )

        fig.show()
        return fig
        """
