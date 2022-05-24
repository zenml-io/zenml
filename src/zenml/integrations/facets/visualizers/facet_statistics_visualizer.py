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

import base64
import os
import tempfile
import webbrowser
from abc import abstractmethod
from typing import Any, Dict, List, Text

import pandas as pd
from facets_overview.generic_feature_statistics_generator import (
    GenericFeatureStatisticsGenerator,
)
from IPython.core.display import HTML, display

import zenml.io.utils
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseStepVisualizer

logger = get_logger(__name__)


class FacetStatisticsVisualizer(BaseStepVisualizer):
    """The base implementation of a ZenML Visualizer."""

    @abstractmethod
    def visualize(
        self, object: StepView, magic: bool = False, *args: Any, **kwargs: Any
    ) -> None:
        """Method to visualize components

        Args:
            object: StepView fetched from run.get_step().
            magic: Whether to render in a Jupyter notebook or not.
        """
        datasets = []
        for output_name, artifact_view in object.outputs.items():
            df = artifact_view.read()
            if type(df) is not pd.DataFrame:
                logger.warning(
                    "`%s` is not a pd.DataFrame. You can only visualize "
                    "statistics of steps that output pandas dataframes. "
                    "Skipping this output.." % output_name
                )
            else:
                datasets.append({"name": output_name, "table": df})
        h = self.generate_html(datasets)
        self.generate_facet(h, magic)

    def generate_html(self, datasets: List[Dict[Text, pd.DataFrame]]) -> str:
        """Generates html for facet.

        Args:
            datasets: List of dicts of dataframes to be visualized as stats.

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
        html_template = zenml.io.utils.read_file_contents_as_string(template)

        html_ = html_template.replace("protostr", protostr)
        return html_

    def generate_facet(self, html_: str, magic: bool = False) -> None:
        """Generate a Facet Overview

        Args:
            html_: HTML represented as a string.
            magic: Whether to magically materialize facet in a notebook.
        """
        if magic:
            if not Environment.in_notebook() or Environment.in_google_colab():
                raise EnvironmentError(
                    "The magic functions are only usable in a Jupyter notebook."
                )
            display(HTML(html_))
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
                zenml.io.utils.write_file_contents_as_string(f.name, html_)
                url = f"file:///{f.name}"
                logger.info("Opening %s in a new browser.." % f.name)
                webbrowser.open(url, new=2)
