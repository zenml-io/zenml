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
import datetime
from typing import Dict, Optional, cast

import pandas as pd
from whylogs import DatasetProfile  # type: ignore

from zenml.integrations.whylogs.whylogs_context import WhylogsContext
from zenml.steps.step_context import StepContext
from zenml.steps.step_interfaces.base_analyzer_step import (
    BaseAnalyzerConfig,
    BaseAnalyzerStep,
)
from zenml.steps.utils import (
    INSTANCE_CONFIGURATION,
    PARAM_CREATED_BY_FUNCTIONAL_API,
    PARAM_ENABLE_CACHE,
)


class WhylogsProfilerConfig(BaseAnalyzerConfig):
    """Config class for the WhylogsProfiler step.

    Attributes:

        dataset_name: the name of the dataset (Optional). If not specified,
            the pipeline step name is used
        dataset_timestamp: timestamp to associate with the generated
            dataset profile (Optional). The current time is used if not
            supplied.
        tags: custom metadata tags associated with the whylogs profile

    Also see `WhylogsContext.log_dataframe`.
    """

    dataset_name: Optional[str] = None
    dataset_timestamp: Optional[datetime.datetime]
    tags: Optional[Dict[str, str]] = None


class WhylogsProfilerStep(BaseAnalyzerStep):
    """Simple step implementation which generates a whylogs data profile from a
    a given pd.DataFrame"""

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        config: WhylogsProfilerConfig,
        context: StepContext,
    ) -> DatasetProfile:
        """Main entrypoint function for the whylogs profiler

        Args:
            dataset: pd.DataFrame, the given dataset
            config: the configuration of the step
            context: the context of the step
        Returns:
            whylogs profile with statistics generated for the input dataset
        """
        whylogs_context = WhylogsContext(context)
        profile = whylogs_context.profile_dataframe(
            dataset, dataset_name=config.dataset_name, tags=config.tags
        )
        return profile


def whylogs_profiler_step(
    step_name: str,
    enable_cache: Optional[bool] = None,
    dataset_name: Optional[str] = None,
    dataset_timestamp: Optional[datetime.datetime] = None,
    tags: Optional[Dict[str, str]] = None,
) -> WhylogsProfilerStep:
    """Shortcut function to create a new instance of the WhylogsProfilerStep step.

    The returned WhylogsProfilerStep can be used in a pipeline to generate a
    whylogs DatasetProfile from a given pd.DataFrame and save it as an artifact.

    Args:
        step_name: The name of the step
        enable_cache: Specify whether caching is enabled for this step. If no
            value is passed, caching is enabled by default
        dataset_name: the dataset name to be used for the whylogs profile
            (Optional). If not specified, the step name is used
        dataset_timestamp: timestamp to associate with the generated
            dataset profile (Optional). The current time is used if not
            supplied.
        tags: custom metadata tags associated with the whylogs profile
    Returns:
        a WhylogsProfilerStep step instance
    """

    # enable cache explicitly to compensate for the fact that this step
    # takes in a context object
    if enable_cache is None:
        enable_cache = True

    step_type = type(
        step_name,
        (WhylogsProfilerStep,),
        {
            INSTANCE_CONFIGURATION: {
                PARAM_ENABLE_CACHE: enable_cache,
                PARAM_CREATED_BY_FUNCTIONAL_API: True,
            },
        },
    )

    return cast(
        WhylogsProfilerStep,
        step_type(
            WhylogsProfilerConfig(
                dataset_name=dataset_name,
                dataset_timestamp=dataset_timestamp,
                tags=tags,
            )
        ),
    )
