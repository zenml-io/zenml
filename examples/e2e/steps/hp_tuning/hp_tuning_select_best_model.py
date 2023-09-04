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


from artifacts.materializer import ModelMetadataMaterializer
from artifacts.model_metadata import ModelMetadata
from typing_extensions import Annotated

from zenml import get_step_context, step
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(output_materializers=ModelMetadataMaterializer)
def hp_tuning_select_best_model(
    search_steps_prefix: str,
) -> Annotated[ModelMetadata, "best_model"]:
    """Find best model across all HP tuning attempts.

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
    for run_step_name, run_step in run.steps.items():
        if run_step_name.startswith(search_steps_prefix):
            for output_name, output in run_step.outputs.items():
                if output_name == "best_model":
                    model: ModelMetadata = output.load()
                    if best_model is None or best_model.metric < model.metric:
                        best_model = model
    ### YOUR CODE ENDS HERE ###
    return best_model or ModelMetadata(None)  # for types compatibility
