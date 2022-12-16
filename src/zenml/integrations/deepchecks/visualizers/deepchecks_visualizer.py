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
"""Implementation of the Deepchecks visualizer."""

import tempfile
import webbrowser
from abc import abstractmethod
from typing import Any, Union

from deepchecks.core.check_result import CheckResult
from deepchecks.core.suite import SuiteResult

from zenml.enums import ArtifactType
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseVisualizer

logger = get_logger(__name__)


class DeepchecksVisualizer(BaseVisualizer):
    """The implementation of a Deepchecks Visualizer."""

    @abstractmethod
    def visualize(self, object: StepView, *args: Any, **kwargs: Any) -> None:
        """Method to visualize components.

        Args:
            object: StepView fetched from run.get_step().
            *args: Additional arguments (unused).
            **kwargs: Additional keyword arguments (unused).
        """
        for artifact_view in object.outputs.values():
            # filter out anything but data analysis artifacts
            if artifact_view.type == ArtifactType.DATA_ANALYSIS:
                artifact = artifact_view.read()
                self.generate_report(artifact)

    def generate_report(self, result: Union[CheckResult, SuiteResult]) -> None:
        """Generate a Deepchecks Report.

        Args:
            result: A SuiteResult.
        """
        print(result)

        if Environment.in_notebook():
            result.show()
        else:
            logger.warning(
                "The magic functions are only usable in a Jupyter notebook."
            )
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".html", encoding="utf-8"
            ) as f:
                result.save_as_html(f)
                url = f"file:///{f.name}"
            logger.info("Opening %s in a new browser.." % f.name)
            webbrowser.open(url, new=2)
