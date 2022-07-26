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
"""Implementation of the whylogs profiler step."""

import datetime
from typing import Optional, cast

import pandas as pd
from whylogs.core import DatasetProfileView  # type: ignore

from zenml.integrations.whylogs.data_validators.whylogs_data_validator import (
    WhylogsDataValidator,
)
from zenml.integrations.whylogs.whylabs_step_decorator import enable_whylabs
from zenml.steps.base_step import BaseStep
from zenml.steps.step_interfaces.base_analyzer_step import (
    BaseAnalyzerConfig,
    BaseAnalyzerStep,
)
from zenml.steps.utils import clone_step


class WhylogsProfilerConfig(BaseAnalyzerConfig):
    """Config class for the WhylogsProfiler step.

    Attributes:
        dataset_timestamp: timestamp to associate with the generated
            dataset profile (Optional). The current time is used if not
            supplied.
    """

    dataset_timestamp: Optional[datetime.datetime]


class WhylogsProfilerStep(BaseAnalyzerStep):
    """Generates a whylogs data profile from a given pd.DataFrame."""

    @staticmethod
    def entrypoint(  # type: ignore[override]
        dataset: pd.DataFrame,
        config: WhylogsProfilerConfig,
    ) -> DatasetProfileView:
        """Main entrypoint function for the whylogs profiler.

        Args:
            dataset: pd.DataFrame, the given dataset
            config: the configuration of the step

        Returns:
            whylogs profile with statistics generated for the input dataset
        """
        data_validator = cast(
            WhylogsDataValidator,
            WhylogsDataValidator.get_active_data_validator(),
        )
        return data_validator.data_profiling(
            dataset, dataset_timestamp=config.dataset_timestamp
        )


def whylogs_profiler_step(
    step_name: str,
    config: WhylogsProfilerConfig,
    dataset_id: Optional[str] = None,
) -> BaseStep:
    """Shortcut function to create a new instance of the WhylogsProfilerStep step.

    The returned WhylogsProfilerStep can be used in a pipeline to generate a
    whylogs DatasetProfileView from a given pd.DataFrame and save it as an
    artifact.

    Args:
        step_name: The name of the step
        config: The step configuration
        dataset_id: Optional dataset ID to use to upload the profile to Whylabs.

    Returns:
        a WhylogsProfilerStep step instance
    """
    step = enable_whylabs(dataset_id=dataset_id)(
        clone_step(WhylogsProfilerStep, step_name)
    )
    return step(config=config)
