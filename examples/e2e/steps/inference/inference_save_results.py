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


import pandas as pd

from zenml import step
from zenml.io.fileio import open


@step
def inference_save_results(predictions: pd.Series, path: str) -> None:
    """Step to save inference results.

    This is an example of a save predictions step that takes the data in and
    stores it in configured artifact store.

    This step is parameterized, which allows you to configure the step
    independently of the step code, before running it in a pipeline.
    In this example, the step can be configured to write to different paths
    in Artifact Store. See the documentation for more information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines


    Args:
        predictions: The predictions.
        path: Path there the predictions will be saved (relative to Artifact Store),

    Returns:
        None.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # TODO: might be redundant
    with open(path, "w") as f:
        predictions.to_csv(f)
    ### YOUR CODE ENDS HERE ###
