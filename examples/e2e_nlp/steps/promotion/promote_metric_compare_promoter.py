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

from typing import Any, Dict

from zenml import get_step_context, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

model_registry = Client().active_stack.model_registry


@step
def promote_metric_compare_promoter(
    latest_metrics: Dict[str, Any],
    current_metrics: Dict[str, Any],
    metric_to_compare: str = "accuracy",
):
    """Try to promote trained model.

    This is an example of a model promotion step. It gets precomputed
    metrics for two model versions, the latest and currently promoted to target environment
    (Production, Staging, etc) and compare them in order to check
    if newly trained model is performing better or not. If new model
    version is better as per the metric - it will get relevant
    tag, otherwise previously promoted model version will remain.

    If the latest version is the only one, it will get promoted automatically.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to use different input data.
    See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        latest_metrics: Recently trained model metrics results.
        current_metrics: Previously promoted model metrics results.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    pipeline_extra = get_step_context().pipeline_run.config.extra
    should_promote = True

    if latest_metrics == current_metrics:
        logger.info("No current model version found - promoting latest")
    else:
        logger.info(
            f"Latest model metric={latest_metrics[metric_to_compare]:.6f}\n"
            f"Current model metric={current_metrics[metric_to_compare]:.6f}"
        )
        if (
            latest_metrics[metric_to_compare]
            < current_metrics[metric_to_compare]
        ):
            logger.info(
                "Current model versions outperformed latest versions - promoting current"
            )

        else:
            logger.info(
                "Latest model versions outperformed current versions - keeping latest"
            )
            should_promote = False

    if should_promote:
        model = get_step_context().model
        model.set_stage(pipeline_extra["target_env"], force=True)

    logger.info(
        f"Promoted current model version to {pipeline_extra['target_env']} environment"
    )
    ### YOUR CODE ENDS HERE ###
