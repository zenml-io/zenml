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
import sys

from zenml.model.gen_ai_helper import (
    construct_json_response_of_failing_steps_for_runs,
    construct_json_response_of_model_version_stats,
    construct_json_response_of_stack_and_components_from_pipeline_run,
    construct_json_response_of_steps_code_from_pipeline_run,
    get_failing_steps_for_runs,
    get_model_version_latest_run,
)


def main(model_version_id: str):  # noqa: D103
    # Get the latest run for a model version
    latest_run = get_model_version_latest_run(model_version_id)
    steps_code = construct_json_response_of_steps_code_from_pipeline_run(
        latest_run
    )
    print(steps_code)
    # Get the stack and components for a run
    stack_and_components = (
        construct_json_response_of_stack_and_components_from_pipeline_run(
            latest_run
        )
    )
    print(stack_and_components)
    # Get the model version run metadata
    model_version_stats = construct_json_response_of_model_version_stats(
        model_version_id
    )
    print(model_version_stats)
    # Get the failing steps for the runs
    failing_steps = construct_json_response_of_failing_steps_for_runs(model_version_id)
    print(failing_steps)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print("Please provide a model version id as an argument.")
