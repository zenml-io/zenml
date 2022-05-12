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

from zenml.integrations.constants import EVIDENTLY, FACETS, MLFLOW, SKLEARN
from zenml.pipelines import pipeline


@pipeline(
    enable_cache=False,
    required_integrations=[SKLEARN, EVIDENTLY, MLFLOW, FACETS],
)
def quickstart_pipeline(
    importer,
    trainer,
    evaluator,
    get_reference_data,
    drift_detector,
    deployment_trigger,
    model_deployer,
):
    """Create a pipeline that trains a model, detects train_serving
    skew, and deploys model based on a threshold."""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)

    reference, comparison = get_reference_data(X_train, X_test)
    drift_report, _ = drift_detector(reference, comparison)

    deployment_decision = deployment_trigger(test_acc)
    model_deployer(deployment_decision, model)
