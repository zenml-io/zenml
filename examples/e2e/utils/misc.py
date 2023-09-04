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


import string

import pandas as pd
from sklearn.datasets import make_classification


def generate_random_data(n_samples: int) -> pd.DataFrame:
    """Generate random data for model input.

    Args:
        n_samples: Number of records to generate.

    Returns:
        pd.DataFrame: Generated dataset for classification task.
    """
    n_features = 20
    X, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_classes=2,
        random_state=42,
    )
    dataset = pd.concat(
        [
            pd.DataFrame(X, columns=list(string.ascii_uppercase[:n_features])),
            pd.Series(y, name="target"),
        ],
        axis=1,
    )
    return dataset
