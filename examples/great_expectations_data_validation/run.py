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


from pipelines.validation import validation_pipeline
from steps.importer import importer
from steps.prevalidator import prevalidator
from steps.profiler import ge_profiler_step
from steps.splitter import splitter
from steps.validator import ge_validate_test_step, ge_validate_train_step

from zenml.integrations.great_expectations.visualizers.ge_visualizer import (
    GreatExpectationsVisualizer,
)
from zenml.post_execution import get_pipeline


def visualize_results(pipeline_name: str, step_name: str) -> None:
    pipeline = get_pipeline(pipeline_name)
    last_run = pipeline.runs[0]
    validation_step = last_run.get_step(step=step_name)
    GreatExpectationsVisualizer().visualize(validation_step)


if __name__ == "__main__":
    pipeline = validation_pipeline(
        importer(),
        splitter(),
        ge_profiler_step,
        prevalidator(),
        ge_validate_train_step,
        ge_validate_test_step,
    )
    pipeline.run()

    visualize_results("validation_pipeline", "profiler")
    visualize_results("validation_pipeline", "train_validator")
    visualize_results("validation_pipeline", "test_validator")
