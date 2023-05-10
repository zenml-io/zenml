#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Initialization for the post-execution artifact class."""

from typing import Any, Optional, Type, cast

from zenml.enums import VisualizationType
from zenml.logger import get_logger
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.base_models import BaseResponseModel
from zenml.post_execution.base_view import BaseView
from zenml.utils.visualization_utils import format_csv_visualization_as_html

logger = get_logger(__name__)


class ArtifactView(BaseView):
    """Post-execution artifact class.

    This can be used to read artifact data that was created during a pipeline
    execution.
    """

    MODEL_CLASS: Type[BaseResponseModel] = ArtifactResponseModel
    REPR_KEYS = ["id", "name", "uri"]

    @property
    def model(self) -> ArtifactResponseModel:
        """Returns the underlying `ArtifactResponseModel`.

        Returns:
            The underlying `ArtifactResponseModel`.
        """
        return cast(ArtifactResponseModel, self._model)

    def read(self) -> Any:
        """Materializes (loads) the data stored in this artifact.

        Returns:
            The materialized data.
        """
        from zenml.utils.artifact_utils import load_artifact

        return load_artifact(self.model)

    def visualize(self, title: Optional[str] = None) -> None:
        """Visualize the artifact in notebook environments.

        Args:
            title: Optional title to show before the visualizations.

        Raises:
            RuntimeError: If not in a notebook environment.
        """
        from IPython.core.display import HTML, Image, Markdown, display

        from zenml.environment import Environment
        from zenml.utils.artifact_utils import load_artifact_visualization

        if not Environment.in_notebook():
            raise RuntimeError(
                "The `output.visualize()` method is only available in Jupyter "
                "notebooks. In all other runtime environments, please open "
                "your ZenML dashboard using `zenml up` and view the "
                "visualizations by clicking on the respective artifacts in the "
                "pipeline run DAG instead."
            )

        if not self.model.visualizations:
            return

        if title:
            display(Markdown(f"### {title}"))
        for i in range(len(self.model.visualizations)):
            visualization = load_artifact_visualization(self.model, index=i)
            if visualization.type == VisualizationType.IMAGE:
                display(Image(visualization.value))
            elif visualization.type == VisualizationType.HTML:
                display(HTML(visualization.value))
            elif visualization.type == VisualizationType.MARKDOWN:
                display(Markdown(visualization.value))
            elif visualization.type == VisualizationType.CSV:
                assert isinstance(visualization.value, str)
                table = format_csv_visualization_as_html(visualization.value)
                display(HTML(table))
            else:
                display(visualization.value)
