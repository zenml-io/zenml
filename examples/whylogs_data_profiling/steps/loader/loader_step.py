#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import whylogs as why
from sklearn import datasets
from whylogs.core import DatasetProfileView  # type: ignore[import]

from zenml.integrations.whylogs.flavors.whylogs_data_validator_flavor import (
    WhylogsDataValidatorSettings,
)
from zenml.steps import Output, step


@step(
    settings={
        "data_validator.whylogs": WhylogsDataValidatorSettings(
            enable_whylabs=True, dataset_id="model-1"
        )
    }
)
def data_loader() -> Output(
    data=pd.DataFrame,
    profile=DatasetProfileView,
):
    """Load the diabetes dataset."""
    X, y = datasets.load_diabetes(return_X_y=True, as_frame=True)

    # merge X and y together
    df = pd.merge(X, y, left_index=True, right_index=True)

    profile = why.log(pandas=df).profile().view()
    return df, profile
