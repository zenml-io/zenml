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
"""Implementation of the Facet Statistics Visualizer."""

import base64
import os
import tempfile
import webbrowser
from abc import abstractmethod
from typing import Any, Dict, List, Text, Union

import pandas as pd
from facets_overview.generic_feature_statistics_generator import (
    GenericFeatureStatisticsGenerator,
)
from IPython.core.display import HTML, display

from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.post_execution.artifact import ArtifactView
from zenml.utils import io_utils
from zenml.visualizers import BaseVisualizer

logger = get_logger(__name__)


class FacetStatisticsVisualizer(BaseVisualizer):
    """Visualize and compare dataset statistics with Facets."""

    @abstractmethod
    def visualize(
        self,
        object: Union[StepView, Dict[str, Union[ArtifactView, pd.DataFrame]]],
        magic: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Method to visualize components.

        Args:
            object: Either a StepView fetched from run.get_step() whose outputs
                are all datasets that should be visualized, or a dict that maps
                dataset names to datasets.
            magic: Whether to render in a Jupyter notebook or not.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        data_dict = object.outputs if isinstance(object, StepView) else object
        datasets = []
        for dataset_name, data in data_dict.items():
            df = data.read() if isinstance(data, ArtifactView) else data
            if type(df) is not pd.DataFrame:
                logger.warning(
                    "`%s` is not a pd.DataFrame. You can only visualize "
                    "statistics of steps that output pandas DataFrames. "
                    "Skipping this output.." % dataset_name
                )
            else:
                datasets.append({"name": dataset_name, "table": df})

        html_ = self.generate_html(datasets)
        self.generate_facet(html_, magic)

    def generate_html(self, datasets: List[Dict[Text, pd.DataFrame]]) -> str:
        """Generates html for facet.

        Args:
            datasets: List of dicts of DataFrames to be visualized as stats.

        Returns:
            HTML template with proto string embedded.
        """
        proto = GenericFeatureStatisticsGenerator().ProtoFromDataFrames(
            datasets
        )
        protostr = base64.b64encode(proto.SerializeToString()).decode("utf-8")

        template = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "stats.html",
        )
        html_template = io_utils.read_file_contents_as_string(template)

        html_ = html_template.replace("protostr", protostr)
        return html_

    def generate_facet(self, html_: str, magic: bool = False) -> None:
        """Generate a Facet Overview.

        Args:
            html_: HTML represented as a string.
            magic: Whether to magically materialize facet in a notebook.

        Raises:
            EnvironmentError: If magic is True and not in a notebook.
        """
        if magic:
            if not (Environment.in_notebook() or Environment.in_google_colab()):
                raise EnvironmentError(
                    "The magic functions are only usable in a Jupyter notebook."
                )
            display(HTML(html_))
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
                io_utils.write_file_contents_as_string(f.name, html_)
                url = f"file:///{f.name}"
                logger.info("Opening %s in a new browser.." % f.name)
                webbrowser.open(url, new=2)
