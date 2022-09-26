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

from zenml.config import DockerSettings
from zenml.integrations.constants import GREAT_EXPECTATIONS, SKLEARN
from zenml.pipelines import pipeline

docker_settings = DockerSettings(
    required_integrations=[SKLEARN, GREAT_EXPECTATIONS]
)


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def validation_pipeline(
    importer, splitter, profiler, prevalidator, train_validator, test_validator
):
    """Data validation pipeline for Great Expectations.

    The pipeline imports data from a source, then splits it into training
    and validation sets. The Great Expectations profiler step is used to
    generate the expectation suite (i.e. validation rules) based on the
    schema ans statistical properties of the training dataset.

    Next, that generated expectation suite is used to validate both the training
    dataset and the validation dataset.

    A prevalidator step is used to delay the execution of the validator
    steps until the generated expectation suite is ready.

    Args:
        importer: data importer step
        splitter: splitter step
        profiler: data profiler step
        prevalidator: dummy step required to enforce ordering
        train_validator: training dataset validation step
        test_validator: test dataset validation step
    """
    imported_data = importer()
    train, test = splitter(imported_data)
    suite = profiler(train)
    condition = prevalidator(suite)
    train_validator(train, condition)
    test_validator(test, condition)
