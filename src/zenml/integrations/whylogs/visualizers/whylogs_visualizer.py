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

import tempfile
from enum import Enum
from typing import Any, List, Optional, cast

from whylogs import DatasetProfile  # type: ignore
from whylogs.viz import ProfileVisualizer, profile_viewer  # type: ignore

from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseStepVisualizer

logger = get_logger(__name__)


class WhylogsPlots(str, Enum):
    """All supported whylogs plot types."""

    distribution = "plot_distribution"
    missing_values = "plot_missing_values"
    uniqueness = "plot_uniqueness"
    data_types = "plot_data_types"
    string_length = "plot_string_length"
    token_length = "plot_token_length"
    char_pos = "plot_char_pos"
    string = "plot_string"

    def __str__(self) -> str:
        """Returns the enum string value."""
        return self.value

    @classmethod
    def list(cls) -> List[str]:
        names = map(lambda c: c.name, cls)  # type: ignore
        return list(cast(List[str], names))


class WhylogsVisualizer(BaseStepVisualizer):
    """The implementation of an Whylogs Visualizer."""

    def visualize(
        self,
        object: StepView,
        *args: Any,
        plots: Optional[List[WhylogsPlots]] = None,
        **kwargs: Any,
    ) -> None:
        """Method to visualize components

        Args:
            object: StepView fetched from run.get_step().
            plots: optional list of whylogs plots to visualize. Defaults to
                using all available plot types if not set
        """
        for artifact_name, artifact_view in object.outputs.items():
            # filter out anything but whylog dataset profile artifacts
            if artifact_view.data_type == ".".join(
                [DatasetProfile.__module__, DatasetProfile.__name__]
            ):
                profile = artifact_view.read()
                # whylogs doesn't currently support visualizing multiple
                # non-related profiles side-by-side, so we open them in
                # separate viewers for now
                self.visualize_profile(artifact_name, profile, plots)

    @staticmethod
    def _get_plot_method(
        visualizer: ProfileVisualizer, plot: WhylogsPlots
    ) -> Any:
        plot_method = getattr(visualizer, plot, None)
        if plot_method is None:
            nl = "\n"
            raise ValueError(
                f"Invalid whylogs plot type: {plot} \n\n"
                f"Valid and supported options are: {nl}- "
                f'{f"{nl}- ".join(WhylogsPlots.list())}'
            )
        return plot_method

    def visualize_profile(
        self,
        name: str,
        profile: DatasetProfile,
        plots: Optional[List[WhylogsPlots]] = None,
    ) -> None:
        """Generate a Facet Overview to visualize a whylogs dataset profile

        Args:
            name: name identifying the profile if multiple profiles are
                displayed at the same time
            profile: whylogs DatasetProfile to visualize
            plots: optional list of whylogs plots to visualize. Defaults to
                using all available plot types if not set
        """
        if self.running_in_notebook():
            from IPython.core.display import display

            if not plots:
                # default to using all plots if none are supplied
                plots = list(WhylogsPlots)

            for column in sorted(profile.columns):
                for plot in plots:
                    visualizer = ProfileVisualizer()
                    visualizer.set_profiles([profile])
                    plot_method = self._get_plot_method(visualizer, plot)
                    display(plot_method(column))
        else:
            logger.warn(
                "The magic functions are only usable in a Jupyter notebook."
            )
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f"-{name}.html"
            ) as f:
                logger.info("Opening %s in a new browser.." % f.name)
                profile_viewer([profile], output_path=f.name)
