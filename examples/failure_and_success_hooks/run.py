#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

import random

from zenml.pipelines import pipeline
from zenml.steps import Output, step
from zenml.pipelines import pipeline
from zenml.steps import Output, step, StepContext
from zenml.environment import Environment


def on_fail(context: StepContext):
    context.step_name
    env = Environment().step_environment
    pipeline_name = env.pipeline_name
    run_name = env.run_name
    context.stack.alerter.ask(
        f"Pipeline {pipeline_name} on Run {run_name} failed on step {env.step_name}!"
    )

@step(enable_cache=False, on_failure=on_fail)
def get_first_num() -> Output(first_num=int):
    """Returns an integer."""
    raise ValueError("Baris was right")
    return 10


@step(enable_cache=False)
def get_random_int() -> Output(random_num=int):
    """Get a random integer between 0 and 10"""
    return random.randint(0, 10)


@step
def subtract_numbers(first_num: int, random_num: int) -> Output(result=int):
    """Subtract random_num from first_num."""
    import time

    time.sleep(10)
    return first_num - random_num


@pipeline()
def hamzas_example_pipeline(get_first_num, get_random_int, subtract_numbers):
    # Link all the steps artifacts together
    first_num = get_first_num()
    random_num = get_random_int()
    subtract_numbers(first_num, random_num)


# NOTE: the airflow DAG object returned by the aep.run() call actually
# needs to be a global object (airflow imports this file and does a for-loop
# over globals() that checks if there are any DAG instances). That's why
# pipelines run via airflow can't have the `__name__=="__main__"` condition

# Run the new pipeline

# aep.write_run_configuration_template('config.yml')
if __name__ == "__main__":
    # Initialize a new pipeline run
    aep = hamzas_example_pipeline(
        get_first_num=get_first_num(),
        get_random_int=get_random_int(),
        subtract_numbers=subtract_numbers(),
    )
    aep.run()
