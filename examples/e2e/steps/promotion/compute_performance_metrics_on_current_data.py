# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import Tuple

import pandas as pd
from sklearn.metrics import accuracy_score
from typing_extensions import Annotated

from zenml import Model, get_step_context, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def compute_performance_metrics_on_current_data(
    dataset_tst: pd.DataFrame,
    target_env: str,
) -> Tuple[
    Annotated[float, "latest_metric"], Annotated[float, "current_metric"]
]:
    """Get metrics for comparison during promotion on fresh dataset.

    This is an example of a metrics calculation step. It computes metric
    on recent test dataset.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to use different input data
    and target environment stage for promotion.
    See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        dataset_tst: The test dataset.

    Returns:
        Latest version and current version metric values on a test set.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    X = dataset_tst.drop(columns=["target"])
    y = dataset_tst["target"].to_numpy()
    logger.info("Evaluating model metrics...")

    # Get model version numbers from Model Control Plane
    latest_version = get_step_context().model
    current_version = Model(name=latest_version.name, version=target_env)

    latest_version_number = latest_version.number
    try:
        current_version_number = current_version.number
    except KeyError:
        current_version_number = None

    if current_version_number is None:
        current_version_number = -1
        metrics = {latest_version_number: 1.0, current_version_number: 0.0}
    else:
        # Get predictors
        predictors = {
            latest_version_number: latest_version.load_artifact("model"),
            current_version_number: current_version.load_artifact("model"),
        }

        metrics = {}
        for version in [latest_version_number, current_version_number]:
            # predict and evaluate
            predictions = predictors[version].predict(X)
            metrics[version] = accuracy_score(y, predictions)

    ### YOUR CODE ENDS HERE ###
    return metrics[latest_version_number], metrics[current_version_number]
