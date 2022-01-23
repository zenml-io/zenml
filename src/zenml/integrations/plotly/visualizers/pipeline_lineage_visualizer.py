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

from abc import abstractmethod
from typing import Any

import pandas as pd
import plotly.express as px
from plotly.graph_objs import Figure

from zenml.logger import get_logger
from zenml.post_execution import PipelineView
from zenml.visualizers import BasePipelineVisualizer

logger = get_logger(__name__)

# TODO [ENG-221]: This integration is working but not really doing much. We
#  should use plotly in more useful ways.


class PipelineLineageVisualizer(BasePipelineVisualizer):
    """Visualize the lineage of runs in a pipeline using plotly."""

    @abstractmethod
    def visualize(
        self, object: PipelineView, *args: Any, **kwargs: Any
    ) -> Figure:
        """Creates a pipeline lineage diagram using plotly."""
        logger.warning(
            "This integration is not completed yet. Results might be unexpected."
        )

        category_dict = {}
        dimensions = ["run"]
        for run in object.runs:
            category_dict[run.name] = {"run": run.name}
            for step in run.steps:
                category_dict[run.name].update(
                    {
                        step.entrypoint_name: str(step.id),
                    }
                )
                if step.entrypoint_name not in dimensions:
                    dimensions.append(f"{step.entrypoint_name}")

        category_df = pd.DataFrame.from_dict(category_dict, orient="index")

        category_df = category_df.reset_index()

        fig = px.parallel_categories(
            category_df,
            dimensions,
            color=None,
            labels="status",
        )

        fig.show()
        return fig
