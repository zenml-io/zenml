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

from utils import promote_in_model_registry

from zenml import Model, get_step_context, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def promote_with_metric_compare(
    latest_metric: float,
    current_metric: float,
    mlflow_model_name: str,
    target_env: str,
) -> None:
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
    In this example, the step can be configured to use precomputed model metrics
    and target environment stage for promotion.
    See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        latest_metric: Recently trained model metric results.
        current_metric: Previously promoted model metric results.
    """

    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    should_promote = True

    # Get model version numbers from Model Control Plane
    latest_version = get_step_context().model
    current_version = Model(name=latest_version.name, version=target_env)

    try:
        current_version_number = current_version.number
    except KeyError:
        current_version_number = None

    if current_version_number is None:
        logger.info("No current model version found - promoting latest")
    else:
        logger.info(
            f"Latest model metric={latest_metric:.6f}\n"
            f"Current model metric={current_metric:.6f}"
        )
        if latest_metric >= current_metric:
            logger.info(
                "Latest model version outperformed current version - promoting latest"
            )
        else:
            logger.info(
                "Current model version outperformed latest version - keeping current"
            )
            should_promote = False

    if should_promote:
        # Promote in Model Control Plane
        model = get_step_context().model
        model.set_stage(stage=target_env, force=True)
        logger.info(f"Current model version was promoted to '{target_env}'.")

        # Promote in Model Registry
        latest_version_model_registry_number = latest_version.run_metadata[
            "model_registry_version"
        ]
        if current_version_number is None:
            current_version_model_registry_number = (
                latest_version_model_registry_number
            )
        else:
            current_version_model_registry_number = (
                current_version.run_metadata["model_registry_version"]
            )
        promote_in_model_registry(
            latest_version=latest_version_model_registry_number,
            current_version=current_version_model_registry_number,
            model_name=mlflow_model_name,
            target_env=target_env.capitalize(),
        )
        promoted_version = latest_version_model_registry_number
    else:
        promoted_version = current_version.run_metadata[
            "model_registry_version"
        ]

    logger.info(
        f"Current model version in `{target_env}` is `{promoted_version}` registered in Model Registry"
    )
    ### YOUR CODE ENDS HERE ###
