#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from datetime import datetime, timedelta

from pipeline import (
    dynamic_importer,
    mnist_pipeline,
    normalize_mnist,
    sklearn_evaluator,
    sklearn_trainer,
)

from zenml.pipelines import Schedule

# Initialize a new pipeline run
scikit_p = mnist_pipeline(
    importer=dynamic_importer(),
    normalizer=normalize_mnist(),
    trainer=sklearn_trainer(),
    evaluator=sklearn_evaluator(),
)

# Run the new pipeline on a Schedule
DAG = scikit_p.run(
    schedule=Schedule(
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(minutes=9),
        interval_second=180,
        catchup=False,
    )
)
