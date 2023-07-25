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
from sklearn.pipeline import Pipeline

from zenml import step


@step
def inference_data_preprocessor(
    dataset_inf: pd.DataFrame, preprocess_pipeline: Pipeline
) -> Annotated[pd.DataFrame, "dataset_inf"]:
    """Data preprocessor step.

    This is an example of a data processor step that prepares the data so that
    it is suitable for model inference. It takes in a dataset as an input step
    artifact and performs any necessary preprocessing steps based on pretrained
    preprocessing pipeline.

    Args:
        dataset_inf: The inferece dataset.
        preprocess_pipeline: Pretrained `Pipeline` to process dataset.

    Returns:
        The processed dataframe: dataset_inf.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    dataset_inf = preprocess_pipeline.transform(dataset_inf)
    ### YOUR CODE ENDS HERE ###

    return dataset_inf
