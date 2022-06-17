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

from pipelines.airflow_example_pipeline import airflow_example_pipeline
from steps.first_num import get_first_num
from steps.random_int import get_random_int
from steps.substract_numbers import subtract_numbers

# Initialize a new pipeline run
aep = airflow_example_pipeline(
    get_first_num=get_first_num(),
    get_random_int=get_random_int(),
    subtract_numbers=subtract_numbers(),
)

# NOTE: the airflow DAG object returned by the aep.run() call actually
# needs to be a global object (airflow imports this file and does a for-loop
# over globals() that checks if there are any DAG instances). That's why
# pipelines run via airflow can't have the `__name__=="__main__"` condition

# Run the new pipeline
DAG = aep.run()

# In case you want to run this on a schedule uncomment the following lines.
# Note that airflow schedules need to be set in the past:

# from datetime import datetime, timedelta
# from zenml.pipelines import Schedule
#
# DAG = aep.run(
#     schedule=Schedule(
#         start_time=datetime.now() - timedelta(hours=1),
#         end_time=datetime.now() + timedelta(minutes=19),
#         interval_second=timedelta(seconds=120),
#         catchup=False,
#     )
# )
