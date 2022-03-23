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
from typing import Any, List, Optional

from whylogs import DatasetProfile  # type: ignore
from whylogs.viz import ProfileVisualizer, profile_viewer  # type: ignore

from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.utils.enum_utils import StrEnum
from zenml.visualizers import BaseStepVisualizer

logger = get_logger(__name__)


class WhylogsPlots(StrEnum):
    """All supported whylogs plot types."""

    DISTRIBUTION = "plot_distribution"
    MISSING_VALUES = "plot_missing_values"
    UNIQUENESS = "plot_uniqueness"
    DATA_TYPES = "plot_data_types"
    STRING_LENGTH = "plot_string_length"
    TOKEN_LENGTH = "plot_token_length"
    CHAR_POS = "plot_char_pos"
    STRING = "plot_string"


class WhylogsVisualizer(BaseStepVisualizer):
    """The implementation of a Whylogs Visualizer."""

    def visualize(
        self,
        object: StepView,
        *args: Any,
        plots: Optional[List[WhylogsPlots]] = None,
        **kwargs: Any,
    ) -> None:
        """Visualize all whylogs dataset profiles present as outputs in the
        step view

        Args:
            object: StepView fetched from run.get_step().
            plots: optional list of whylogs plots to visualize. Defaults to
                using all available plot types if not set
        """
        whylogs_artifact_datatype = (
            f"{DatasetProfile.__module__}.{DatasetProfile.__name__}"
        )
        for artifact_name, artifact_view in object.outputs.items():
            # filter out anything but whylog dataset profile artifacts
            if artifact_view.data_type == whylogs_artifact_datatype:
                profile = artifact_view.read()
                # whylogs doesn't currently support visualizing multiple
                # non-related profiles side-by-side, so we open them in
                # separate viewers for now
                self.visualize_profile(artifact_name, profile, plots)

    @staticmethod
    def _get_plot_method(
        visualizer: ProfileVisualizer, plot: WhylogsPlots
    ) -> Any:
        """Get the Whylogs ProfileVisualizer plot method corresponding to a
        WhylogsPlots enum value.

        Args:
            visualizer: a ProfileVisualizer instance
            plot: a WhylogsPlots enum value

        Raises:
            ValueError: if the supplied WhylogsPlots enum value does not
                correspond to a valid ProfileVisualizer plot method

        Returns:
            The ProfileVisualizer plot method corresponding to the input
            WhylogsPlots enum value
        """
        plot_method = getattr(visualizer, plot, None)
        if plot_method is None:
            nl = "\n"
            raise ValueError(
                f"Invalid whylogs plot type: {plot} \n\n"
                f"Valid and supported options are: {nl}- "
                f'{f"{nl}- ".join(WhylogsPlots.names())}'
            )
        return plot_method

    def visualize_profile(
        self,
        name: str,
        profile: DatasetProfile,
        plots: Optional[List[WhylogsPlots]] = None,
    ) -> None:
        """Generate a visualization of a whylogs dataset profile.

        Args:
            name: name identifying the profile if multiple profiles are
                displayed at the same time
            profile: whylogs DatasetProfile to visualize
            plots: optional list of whylogs plots to visualize. Defaults to
                using all available plot types if not set
        """
        if Environment.in_notebook():
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
            logger.warning(
                "The magic functions are only usable in a Jupyter notebook."
            )
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f"-{name}.html"
            ) as f:
                logger.info("Opening %s in a new browser.." % f.name)
                profile_viewer([profile], output_path=f.name)
