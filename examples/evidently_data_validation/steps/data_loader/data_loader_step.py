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
import os

import pandas as pd
from sklearn import datasets

from zenml.steps import step


@step
def data_loader() -> pd.DataFrame:
    """Load the OpenML women's e-commerce clothing reviews dataset."""
    reviews_data = datasets.fetch_openml(
        name="Womens-E-Commerce-Clothing-Reviews",
        version=2,
        as_frame="auto",
        data_home=os.path.join(os.getcwd(), "data"),
    )
    reviews = reviews_data.frame
    return reviews
