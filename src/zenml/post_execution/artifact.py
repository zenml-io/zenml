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

from typing import TYPE_CHECKING, Any, Optional, Type, cast

from zenml.enums import VisualizationType
from zenml.logger import get_logger
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.base_models import BaseResponseModel
from zenml.post_execution.base_view import BaseView

if TYPE_CHECKING:
    from zenml.materializers.base_materializer import BaseMaterializer


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

    def read(
        self,
        output_data_type: Optional[Type[Any]] = None,
        materializer_class: Optional[Type["BaseMaterializer"]] = None,
    ) -> Any:
        """Materializes the data stored in this artifact.

        Args:
            output_data_type: Deprecated; will be ignored.
            materializer_class: Deprecated; will be ignored.

        Returns:
            The materialized data.
        """
        if output_data_type is not None:
            logger.warning(
                "The `output_data_type` argument is deprecated and will be "
                "removed in a future release."
            )
        if materializer_class is not None:
            logger.warning(
                "The `materializer_class` argument is deprecated and will be "
                "removed in a future release."
            )

        from zenml.utils.materializer_utils import load_artifact

        return load_artifact(self.model)

    def visualize(self, index: int = 0) -> None:
        """Visualize the artifact in notebook environments.

        Args:
            index: Index of the visualization to get (if there are multiple).

        Raises:
            RuntimeError: If no visualizations are found.
            IndexError: If the index is out of range.
        """
        from IPython.core.display import HTML, Image, display

        from zenml.environment import Environment
        from zenml.utils.materializer_utils import load_visualization

        if not self.model.visualizations:
            raise RuntimeError(
                "No visualizations found for this artifact. Nothing to show."
            )

        if index < 0 or index >= len(self.model.visualizations):
            raise IndexError(
                f"Index {index} out of range. The artifact only has "
                f"{len(self.model.visualizations)} visualizations."
            )

        if not Environment.in_notebook() and not Environment.in_google_colab():
            raise RuntimeError(
                "The `output.visualize()` method is only usable in Jupyter "
                "notebooks. In all other runtime environments, please open "
                "your ZenML dashboard using `zenml up` and view the "
                "visualization by clicking on the respective artifact in the "
                "pipeline run DAG instead."
            )

        visualization = self.model.visualizations[index]
        value = load_visualization(visualization)

        if visualization.type == VisualizationType.IMAGE:
            display(Image(value))
        elif visualization.type == VisualizationType.HTML:
            display(HTML(value))
        else:
            raise RuntimeError(
                f"Visualization type {visualization.type} cannot be displayed "
                "in a notebook environment. Please open your ZenML dashboard "
                "using `zenml up` and view the visualization by clicking on "
                "the respective artifact in the pipeline run DAG instead."
            )
