#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import pandas as pd
from deepchecks.tabular.datasets.classification import iris
from sklearn.model_selection import train_test_split

from zenml.steps import Output, step


@step
def data_loader() -> Output(
    reference_dataset=pd.DataFrame, comparison_dataset=pd.DataFrame
):
    """Load the iris dataset."""
    iris_df = iris.load_data(data_format="Dataframe", as_train_test=False)
    label_col = "target"
    df_train, df_test = train_test_split(
        iris_df, stratify=iris_df[label_col], random_state=0
    )
    return df_train, df_test
