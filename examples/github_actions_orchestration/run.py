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
import random

from zenml.pipelines import pipeline
from zenml.steps import Output, step


@step
def get_first_num() -> Output(first_num=int):
    """Returns an integer."""
    return 10


@step
def get_random_int() -> Output(random_num=int):
    """Get a random integer between 0 and 10"""
    return random.randint(0, 10)


@step
def subtract_numbers(first_num: int, random_num: int) -> Output(result=int):
    """Subtract random_num from first_num."""
    return first_num - random_num


@pipeline(enable_cache=False)
def example_pipeline(get_first_num, get_random_int, subtract_numbers):
    # Link all the steps together
    first_num = get_first_num()
    random_num = get_random_int()
    subtract_numbers(first_num, random_num)


if __name__ == "__main__":
    pipeline_instance = example_pipeline(
        get_first_num=get_first_num(),
        get_random_int=get_random_int(),
        subtract_numbers=subtract_numbers(),
    )

    pipeline_instance.run()

    # If you want to run your pipeline on a schedule instead, you need to pass
    # in a `Schedule` object with a cron expression. Note that for the schedule
    # to get active, you'll need to merge the GitHub Actions workflow into your
    # GitHub default branch. To see it in action, uncomment the following lines:

    # from zenml.pipelines import Schedule
    # pipeline_instance.run(
    #     schedule=Schedule(cron_expression="* 1 * * *")
    # )
