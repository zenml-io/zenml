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


from zenml.pipelines import pipeline
from zenml.steps import step


@step
def constant_int_output_test_step() -> int:
    return 7


@step
def int_plus_one_test_step(input: int) -> int:
    return input + 1


@pipeline(name="connected_two_step_pipeline")
def connected_two_step_pipeline(step_1, step_2):
    """Pytest fixture that returns a pipeline which takes two steps
    `step_1` and `step_2` that are connected."""
    step_2(step_1())


pipeline_instance = connected_two_step_pipeline(
    step_1=constant_int_output_test_step(),
    step_2=int_plus_one_test_step(),
)
