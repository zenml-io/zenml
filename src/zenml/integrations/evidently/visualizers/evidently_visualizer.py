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
"""Implementation of the Evidently visualizer."""

import tempfile
import webbrowser
from abc import abstractmethod
from typing import Any

from zenml.enums import ArtifactType
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseVisualizer

logger = get_logger(__name__)


class EvidentlyVisualizer(BaseVisualizer):
    """The implementation of an Evidently Visualizer."""

    @abstractmethod
    def visualize(self, object: StepView, *args: Any, **kwargs: Any) -> None:
        """Method to visualize components.

        Args:
            object: StepView fetched from run.get_step().
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        for artifact_view in object.outputs.values():
            # filter out anything but data artifacts
            if (
                artifact_view.type == ArtifactType.DATA
                and artifact_view.data_type == "builtins.str"
            ):
                artifact = artifact_view.read()
                self.generate_facet(artifact)

    def generate_facet(self, html_: str) -> None:
        """Generate a Facet Overview.

        Args:
            html_: HTML represented as a string.
        """
        if Environment.in_notebook() or Environment.in_google_colab():
            from IPython.core.display import HTML, display

            display(HTML(html_))
        else:
            logger.warning(
                "The magic functions are only usable in a Jupyter notebook."
            )
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".html", encoding="utf-8"
            ) as f:
                f.write(html_)
                url = f"file:///{f.name}"
                logger.info("Opening %s in a new browser.." % f.name)
                webbrowser.open(url, new=2)
