#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from typing import Optional

from pipelines import data_profiling_pipeline
from steps import (
    data_loader,
    data_splitter,
    test_data_profiler,
    train_data_profiler,
)

from zenml.integrations.whylogs.visualizers import WhylogsVisualizer
from zenml.logger import get_logger
from zenml.post_execution import get_pipeline

logger = get_logger(__name__)


def visualize_statistics(
    step_name: str, reference_step_name: Optional[str] = None
) -> None:
    """Helper function to visualize whylogs statistics from step artifacts.

    Args:
        step_name: step that generated and returned a whylogs profile
        reference_step_name: an optional second step that generated a whylogs
            profile to use for data drift visualization where two whylogs
            profiles are required.
    """
    pipe = get_pipeline(pipeline="data_profiling_pipeline")
    whylogs_step = pipe.runs[0].get_step(step=step_name)
    whylogs_reference_step = None
    if reference_step_name:
        whylogs_reference_step = pipe.runs[0].get_step(
            name=reference_step_name
        )

    WhylogsVisualizer().visualize(
        whylogs_step,
        reference_step_view=whylogs_reference_step,
    )


if __name__ == "__main__":

    pipeline_instance = data_profiling_pipeline(
        data_loader=data_loader(),
        data_splitter=data_splitter(),
        train_data_profiler=train_data_profiler,
        test_data_profiler=test_data_profiler,
    )

    pipeline_instance.run()

    visualize_statistics("data_loader")
    visualize_statistics("train_data_profiler", "test_data_profiler")
