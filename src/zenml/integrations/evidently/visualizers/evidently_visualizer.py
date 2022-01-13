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

import tempfile
import webbrowser
from abc import abstractmethod
from typing import Any

import zenml.io.utils
from zenml.artifacts import DataAnalysisArtifact
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseStepVisualizer

logger = get_logger(__name__)


class EvidentlyVisualizer(BaseStepVisualizer):
    """The implementation of an Evidently Visualizer."""

    @abstractmethod
    def visualize(self, object: StepView, *args: Any, **kwargs: Any) -> None:
        """Method to visualize components

        Args:
            object: StepView fetched from run.get_step().
        """
        for artifact_view in object.outputs.values():
            # filter out anything but data analysis artifacts
            if (
                artifact_view.type == DataAnalysisArtifact.__name__
                and artifact_view.data_type == "builtins.str"
            ):
                artifact = artifact_view.read()
                self.generate_facet(artifact)

    def generate_facet(self, html_: str) -> None:
        """Generate a Facet Overview

        Args:
            h: HTML represented as a string.
        """
        if self.running_in_notebook():
            from IPython.core.display import HTML, display

            display(HTML(html_))
        else:
            logger.warn(
                "The magic functions are only usable in a Jupyter notebook."
            )
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
                zenml.io.utils.write_file_contents_as_string(f.name, html_)
                url = f"file:///{f.name}"
                logger.info("Opening %s in a new browser.." % f.name)
                webbrowser.open(url, new=2)
