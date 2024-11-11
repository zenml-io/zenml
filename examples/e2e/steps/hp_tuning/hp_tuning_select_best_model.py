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


from typing import List

from sklearn.base import ClassifierMixin
from typing_extensions import Annotated

from zenml import get_step_context, step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def hp_tuning_select_best_model(
    step_names: List[str],
) -> Annotated[ClassifierMixin, "best_model"]:
    """Find best model across all HP tuning attempts.

    This is an example of a model hyperparameter tuning step that loops
    other artifacts linked to model version in Model Control Plane to find
    the best hyperparameter tuning output model of all according to the metric.

    Returns:
        The best possible model class and its' parameters.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    model = get_step_context().model

    best_model = None
    best_metric = -1
    # consume artifacts attached to current model version in Model Control Plane
    for step_name in step_names:
        hp_output = model.get_data_artifact("hp_result")
        model_: ClassifierMixin = hp_output.load()
        # fetch metadata we attached earlier
        metric = float(hp_output.run_metadata["metric"])
        if best_model is None or best_metric < metric:
            best_model = model_
    ### YOUR CODE ENDS HERE ###
    return best_model
