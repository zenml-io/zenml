# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
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


import pandas as pd
from sklearn.metrics import accuracy_score
from typing_extensions import Annotated

from zenml import step
from zenml.client import Client
from zenml.integrations.mlflow.services import MLFlowDeploymentService
from zenml.logger import get_logger

logger = get_logger(__name__)

model_registry = Client().active_stack.model_registry


@step
def promote_get_metric(
    dataset_tst: pd.DataFrame,
    deployment_service: MLFlowDeploymentService,
) -> Annotated[float, "metric"]:
    """Get metric for comparison for one model deployment.

    This is an example of a metric calculation step. It get a model deployment
    service and computes metric on recent test dataset.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to use different input data.
    See the documentation for more information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines

    Args:
        dataset_tst: The test dataset.
        deployment_service: Model version deployment.

    Returns:
        Metric value for a given deployment on test set.

    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    X = dataset_tst.drop(columns=["target"])
    y = dataset_tst["target"]
    logger.info("Evaluating model metrics...")

    predictions = deployment_service.predict(request=X)
    metric = accuracy_score(y, predictions)
    deployment_service.deprovision(force=True)
    ### YOUR CODE ENDS HERE ###
    return metric
