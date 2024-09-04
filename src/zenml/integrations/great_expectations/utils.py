#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Great Expectations data profiling standard step."""

from typing import Any, Dict, Optional, Tuple

import pandas as pd
from great_expectations.core.batch_definition import BatchDefinition
from great_expectations.data_context.data_context.abstract_data_context import (
    AbstractDataContext,
)

from zenml import get_step_context
from zenml.logger import get_logger
from zenml.utils.string_utils import random_str

logger = get_logger(__name__)


def create_batch_definition(
    context: AbstractDataContext,
    dataset: pd.DataFrame,
    data_asset_name: Optional[str],
) -> Tuple[BatchDefinition, Dict[str, Any]]:
    """Create a temporary runtime GE batch request from a dataset step artifact.

    Args:
        context: Great Expectations data context.
        dataset: Input dataset.
        data_asset_name: Optional custom name for the data asset.

    Returns:
        A Great Expectations runtime batch request.
    """
    try:
        # get pipeline name, step name and run id
        step_context = get_step_context()
        pipeline_name = step_context.pipeline.name
        run_name = step_context.pipeline_run.name
        step_name = step_context.step_run.name
    except RuntimeError:
        # if not running inside a pipeline step, use random values
        pipeline_name = f"pipeline_{random_str(5)}"
        run_name = f"pipeline_{random_str(5)}"
        step_name = f"step_{random_str(5)}"

    datasource_name = f"{run_name}_{step_name}"
    data_asset_name = data_asset_name or f"{pipeline_name}_{step_name}"
    batch_definition_name = "default"

    data_source = context.data_sources.add_pandas(name=datasource_name)
    data_asset = data_source.add_dataframe_asset(name=data_asset_name)

    batch_definition = data_asset.add_batch_definition_whole_dataframe(
        batch_definition_name
    )

    batch_parameters = {"dataframe": dataset}

    return batch_definition, batch_parameters
