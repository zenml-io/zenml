#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Implementation of the whylogs visualizer step."""

import tempfile
import webbrowser
from typing import Any, Optional, cast

from whylogs.core import DatasetProfileView  # type: ignore
from whylogs.viz import NotebookProfileVisualizer  # type: ignore

from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseVisualizer

logger = get_logger(__name__)


class WhylogsVisualizer(BaseVisualizer):
    """The implementation of a Whylogs Visualizer."""

    def visualize(
        self,
        object: StepView,
        reference_step_view: Optional[StepView] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Visualize whylogs dataset profiles present as outputs in the step view.

        Args:
            object: StepView fetched from run.get_step().
            reference_step_view: second StepView fetched from run.get_step() to
                use as a reference to visualize data drift
            *args: additional positional arguments to pass to the visualize
                method
            **kwargs: additional keyword arguments to pass to the visualize
                method
        """

        def extract_profile(
            step_view: StepView,
        ) -> Optional[DatasetProfileView]:
            """Extract a whylogs DatasetProfileView from a step view.

            Args:
                step_view: a step view

            Returns:
                A whylogs DatasetProfileView object loaded from the step view,
                if one could be found, otherwise None.
            """
            whylogs_artifact_datatype = (
                f"{DatasetProfileView.__module__}.{DatasetProfileView.__name__}"
            )
            for _, artifact_view in step_view.outputs.items():
                # filter out anything but whylogs dataset profile artifacts
                if artifact_view.data_type == whylogs_artifact_datatype:
                    profile = artifact_view.read()
                    return cast(DatasetProfileView, profile)
            return None

        profile = extract_profile(object)
        reference_profile: Optional[DatasetProfileView] = None
        if reference_step_view:
            reference_profile = extract_profile(reference_step_view)

        self.visualize_profile(profile, reference_profile)

    def visualize_profile(
        self,
        profile: DatasetProfileView,
        reference_profile: Optional[DatasetProfileView] = None,
    ) -> None:
        """Generate a visualization of one or two whylogs dataset profile.

        Args:
            profile: whylogs DatasetProfileView to visualize
            reference_profile: second optional DatasetProfileView to use to
                generate a data drift visualization
        """
        # currently, whylogs doesn't support visualizing a single profile, so
        # we trick it by using the same profile twice, both as reference and
        # target, in a drift report
        reference_profile = reference_profile or profile
        visualization = NotebookProfileVisualizer()
        visualization.set_profiles(
            target_profile_view=profile,
            reference_profile_view=reference_profile,
        )
        rendered_html = visualization.summary_drift_report()

        if Environment.in_notebook():
            from IPython.core.display import display

            display(rendered_html)
            for column in sorted(list(profile.get_columns().keys())):
                display(visualization.double_histogram(feature_name=column))
        else:
            logger.warning(
                "The magic functions are only usable in a Jupyter notebook."
            )
            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".html", encoding="utf-8"
            ) as f:
                f.write(rendered_html.data)
                url = f"file:///{f.name}"
            logger.info("Opening %s in a new browser.." % f.name)
            webbrowser.open(url, new=2)
