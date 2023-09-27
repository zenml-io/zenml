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


from config import MetaConfig

from zenml import step
from zenml.client import Client
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import ModelVersionStage

logger = get_logger(__name__)

model_registry = Client().active_stack.model_registry


@step
def promote_metric_compare_promoter(
    latest_metric: float,
    current_metric: float,
    latest_version: str,
    current_version: str,
):
    """Try to promote trained model.

    This is an example of a model promotion step. It gets precomputed
    metrics for 2 model version: latest and currently promoted to target environment
    (Production, Staging, etc) and compare than in order to define
    if newly trained model is performing better or not. If new model
    version is better by metric - it will get relevant
    tag, otherwise previously promoted model version will remain.

    If the latest version is the only one - it will get promoted automatically.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to use different input data.
    See the documentation for more information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines

    Args:
        latest_metric: Recently trained model metric results.
        current_metric: Previously promoted model metric results.
        latest_version: Recently trained model version.
        current_version:Previously promoted model version.

    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    should_promote = True

    if latest_version == current_version:
        logger.info("No current model version found - promoting latest")
    else:
        logger.info(
            f"Latest model metric={latest_metric:.6f}\n"
            f"Current model metric={current_metric:.6f}"
        )
        if latest_metric > current_metric:
            logger.info(
                "Latest model versions outperformed current versions - promoting latest"
            )
        else:
            logger.info(
                "Current model versions outperformed latest versions - keeping current"
            )
            should_promote = False

    promoted_version = current_version
    if should_promote:
        if latest_version != current_version:
            model_registry.update_model_version(
                name=MetaConfig.mlflow_model_name,
                version=current_version,
                stage=ModelVersionStage.ARCHIVED,
            )
        model_registry.update_model_version(
            name=MetaConfig.mlflow_model_name,
            version=latest_version,
            stage=MetaConfig.target_env,
        )
        promoted_version = latest_version

    logger.info(
        f"Current model version in `{MetaConfig.target_env.value}` is `{promoted_version}`"
    )
    ### YOUR CODE ENDS HERE ###
