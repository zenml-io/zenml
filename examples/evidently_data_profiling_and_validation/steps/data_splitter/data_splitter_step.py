#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from zenml.steps import Output, step


@step
def data_splitter(
    reviews: pd.DataFrame,
) -> Output(reference_dataset=pd.DataFrame, comparison_dataset=pd.DataFrame):
    """Splits the dataset into two subsets, the reference dataset and the
    comparison dataset.
    """
    ref_df = reviews[reviews.Rating > 3].sample(
        n=5000, replace=True, ignore_index=True, random_state=42
    )
    comp_df = reviews[reviews.Rating < 3].sample(
        n=5000, replace=True, ignore_index=True, random_state=42
    )
    return ref_df, comp_df
