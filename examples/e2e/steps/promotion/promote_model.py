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


from typing import Annotated

import pandas as pd
from config import MetaConfig
from sklearn.metrics import accuracy_score

from zenml import step
from zenml.client import Client
from zenml.integrations.mlflow.services import MLFlowDeploymentService
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    mlflow_model_registry_deployer_step,
)
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import ModelVersionStage

logger = get_logger(__name__)

model_registry = Client().active_stack.model_registry


@step
def promote_model(
    dataset_tst: pd.DataFrame,
) -> Annotated[str, "model_version"]:
    """Try to promote trained model.

    This is an example of a model promotion step. It will retrieve 2 model
    versions from Model Registry: latest and currently promoted to target
    environment (Production, Staging, etc) and compare than on recent test
    dataset in order to define if newly trained model is performing better
    or not. If new model version is better by metric - it will get relevant
    tag, otherwise previously promoted model version will remain.

    Args:
        dataset_tst: The test dataset.

    Returns:
        The model version of best model.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###

    # TODO: change to `get_latest_model_version` after FRW-2163
    target_versions = model_registry.list_model_versions(
        name=MetaConfig.mlflow_model_name,
        metadata={},
        stage=MetaConfig.target_env,
    )
    none_versions = model_registry.list_model_versions(
        name=MetaConfig.mlflow_model_name,
        metadata={},
        stage=None,
    )
    latest_versions = none_versions[0]
    current_version = None
    should_promote = True
    if target_versions:
        current_version = target_versions[0]
        X = dataset_tst.drop(columns=["target"])
        y = dataset_tst["target"]
        logger.info("Evaluating latest model metrics...")

        latest_deployment: MLFlowDeploymentService = (
            mlflow_model_registry_deployer_step(
                registry_model_name=MetaConfig.mlflow_model_name,
                registry_model_version=latest_versions.version,
            )
        )
        latest_predictions = latest_deployment.predict(request=X)
        latest_accuracy = accuracy_score(y, latest_predictions)

        logger.info(
            f"Evaluating `{MetaConfig.target_env.value}` model metrics..."
        )
        current_deployment: MLFlowDeploymentService = (
            mlflow_model_registry_deployer_step(
                registry_model_name=MetaConfig.mlflow_model_name,
                registry_model_version=current_version.version,
            )
        )
        current_predictions = current_deployment.predict(request=X)
        current_accuracy = accuracy_score(y, current_predictions)
        logger.info(
            f"Latest model accuracy is {latest_accuracy*100:.2f}%, current model accuracy is {current_accuracy*100:.2f}%"
        )

        if latest_accuracy > current_accuracy:
            logger.info(
                "Latest model versions outperformed current versions - promoting latest"
            )
        else:
            logger.info(
                "Current model versions outperformed latest versions - keeping current"
            )
            should_promote = False
    else:
        logger.info("No current model version found - promoting latest")

    if should_promote:
        if current_version:
            model_registry.update_model_version(
                name=MetaConfig.mlflow_model_name,
                version=current_version.version,
                stage=ModelVersionStage.ARCHIVED,
                metadata={},
            )
        model_registry.update_model_version(
            name=MetaConfig.mlflow_model_name,
            version=latest_versions.version,
            stage=MetaConfig.target_env,
            metadata={},
        )

    current_version = model_registry.list_model_versions(
        name=MetaConfig.mlflow_model_name,
        metadata={},
        stage=MetaConfig.target_env,
    )[0].version
    logger.info(
        f"Current model version in `{MetaConfig.target_env.value}` is `{current_version}`"
    )

    return current_version
