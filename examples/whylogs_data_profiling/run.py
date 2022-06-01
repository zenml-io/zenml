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

from whylogs import DatasetProfile  # type: ignore

from steps.profiler.profiler_step import (train_data_profiler,
                                          test_data_profiler)
from steps.splitter.splitter_step import data_splitter
from steps.loader.loader_step import data_loader
from pipelines.profiling_pipeline.profiling_pipeline import \
    data_profiling_pipeline
from zenml.integrations.whylogs.visualizers import WhylogsVisualizer
from zenml.logger import get_logger
from zenml.repository import Repository

logger = get_logger(__name__)


def visualize_statistics(step_name: str):
    repo = Repository()
    pipe = repo.get_pipeline(pipeline_name="data_profiling_pipeline")
    whylogs_outputs = pipe.runs[-1].get_step(name=step_name)
    WhylogsVisualizer().visualize(whylogs_outputs)


if __name__ == "__main__":

    p = data_profiling_pipeline(
        data_loader=data_loader(),
        data_splitter=data_splitter(),
        train_data_profiler=train_data_profiler,
        test_data_profiler=test_data_profiler,
    )

    p.run()

    visualize_statistics("data_loader")
    visualize_statistics("train_data_profiler")
    visualize_statistics("test_data_profiler")
