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

from typing import Any

import pandas as pd
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def inference_predict(
    model: Any,
    dataset_inf: pd.DataFrame,
) -> Annotated[pd.Series, "predictions"]:
    """Predictions step.

    This is an example of a predictions step that takes the data and model in
    and returns predicted values.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to use different input data.
    See the documentation for more information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        model: Trained model.
        dataset_inf: The inference dataset.

    Returns:
        The predictions as pandas series
    """
    # run prediction from memory
    predictions = model.predict(dataset_inf)

    predictions = pd.Series(predictions, name="predicted")
    return predictions
