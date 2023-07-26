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


from typing import Annotated, Any, Dict

from utils.sklearn_materializer import ClassifierMixinMaterializer

from zenml import get_step_context, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(output_materializers=ClassifierMixinMaterializer)
def hp_tuning_select_best_model(
    search_steps_prefix: str,
) -> Annotated[Dict[str, Any], "best_model"]:
    """Find best model across all HP tunning attempts.

    This is an example of a model hyperparameter tuning step that takes
    in prefix of steps called previously to search for best hyperparameters.
    It will loop other them and find best model of all according to metric.

    Args:
        search_steps_prefix: Prefix of steps used for grid search before.

    Returns:
        The best possible model class and its' parameters.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    run_name = get_step_context().pipeline_run.name
    run = Client().get_pipeline_run(run_name)

    best_model = None
    for step_name, step in run.steps.items():
        if step_name.startswith(search_steps_prefix):
            for output_name, output in step.outputs.items():
                if output_name == "best_model":
                    model = output.load()
                    if (
                        best_model is None
                        or best_model["metric"] < model["metric"]
                    ):
                        best_model = model
    ### YOUR CODE ENDS HERE ###
    return best_model or {}  # for types compatibility
