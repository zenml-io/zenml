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
"""Implementation of the FacetsMaterializer."""

import base64
import os
from typing import Dict

from facets_overview.generic_feature_statistics_generator import (
    GenericFeatureStatisticsGenerator,
)

from zenml.enums import ArtifactType, VisualizationType
from zenml.integrations.facets.models import (
    FacetsComparison,
)
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

VISUALIZATION_FILENAME = "visualization.html"


class FacetsMaterializer(BaseMaterializer):
    """Materializer to save Facets visualizations.

    This materializer is used to visualize and compare dataset statistics using
    Facets. In contrast to other materializers, this materializer only saves
    the visualization and not the data itself.
    """

    ASSOCIATED_TYPES = (FacetsComparison,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA_ANALYSIS

    def save_visualizations(
        self, data: FacetsComparison
    ) -> Dict[str, VisualizationType]:
        """Save a Facets visualization of the data.

        Args:
            data: The data to visualize.

        Returns:
            A dictionary of visualization URIs and their types.
        """
        proto = GenericFeatureStatisticsGenerator().ProtoFromDataFrames(
            data.datasets
        )
        protostr = base64.b64encode(proto.SerializeToString()).decode("utf-8")
        template = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "stats.html",
        )
        html = io_utils.read_file_contents_as_string(template)
        html = html.replace("protostr", protostr)
        visualization_path = os.path.join(self.uri, VISUALIZATION_FILENAME)
        visualization_path = visualization_path.replace("\\", "/")
        with fileio.open(visualization_path, "w") as f:
            f.write(html)
        return {visualization_path: VisualizationType.HTML}
