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

from zenml import step
from zenml.integrations.whylogs.data_validators.whylogs_data_validator import (
    WhylogsDataValidator,
)
from zenml.integrations.whylogs.flavors import WhylogsDataValidatorFlavor
from zenml.integrations.whylogs.flavors.whylogs_data_validator_flavor import (
    WhylogsDataValidatorSettings,
)
from zenml.steps.base_step import BaseStep
from zenml.utils import settings_utils


@step
def whylogs_profiler_step(
    dataset: pd.DataFrame,
    dataset_timestamp: Optional[datetime.datetime] = None,
) -> DatasetProfileView:
    """Generate a whylogs `DatasetProfileView` from a given `pd.DataFrame`.

    Args:
        dataset: The dataset to generate the profile for.
        dataset_timestamp: The timestamp of the dataset.

    Returns:
        whylogs profile with statistics generated for the input dataset.
    """
    data_validator = cast(
        WhylogsDataValidator,
        WhylogsDataValidator.get_active_data_validator(),
    )
    return data_validator.data_profiling(
        dataset, dataset_timestamp=dataset_timestamp
    )


def get_whylogs_profiler_step(
    dataset_timestamp: Optional[datetime.datetime] = None,
    dataset_id: Optional[str] = None,
    enable_whylabs: bool = True,
) -> BaseStep:
    """Shortcut function to create a new instance of the WhylogsProfilerStep step.

    The returned WhylogsProfilerStep can be used in a pipeline to generate a
    whylogs DatasetProfileView from a given pd.DataFrame and save it as an
    artifact.

    Args:
        dataset_timestamp: The timestamp of the dataset.
        dataset_id: Optional dataset ID to use to upload the profile to Whylabs.
        enable_whylabs: Whether to upload the generated profile to Whylabs.

    Returns:
        a WhylogsProfilerStep step instance
    """
    key = settings_utils.get_flavor_setting_key(WhylogsDataValidatorFlavor())
    settings = WhylogsDataValidatorSettings(
        enable_whylabs=enable_whylabs, dataset_id=dataset_id
    )
    step_instance = whylogs_profiler_step.with_options(
        parameters={"dataset_timestamp": dataset_timestamp},
        settings={key: settings},
    )
    return step_instance
