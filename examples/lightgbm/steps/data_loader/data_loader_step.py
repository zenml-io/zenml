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
import tempfile

import lightgbm as lgb
import pandas as pd
import requests

from zenml import step
from zenml.steps import Output

TRAIN_SET_RAW = "https://raw.githubusercontent.com/microsoft/LightGBM/master/examples/regression/regression.train"

TEST_SET_RAW = "https://raw.githubusercontent.com/microsoft/LightGBM/master/examples/regression/regression.test"


@step
def data_loader() -> Output(mat_train=lgb.Dataset, mat_test=lgb.Dataset):
    """Retrieves the data from the demo directory of the LightGBM repo."""
    # Write data to temporary files to load it with `lgb.Dataset`.
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".html", encoding="utf-8"
    ) as f:
        f.write(requests.get(TRAIN_SET_RAW).text)
        df_train = pd.read_csv(f.name, header=None, sep="\t")

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".html", encoding="utf-8"
    ) as f:
        f.write(requests.get(TEST_SET_RAW).text)
        df_test = pd.read_csv(f.name, header=None, sep="\t")

    # Parse data
    y_train = df_train[0]
    y_test = df_test[0]
    X_train = df_train.drop(0, axis=1)
    X_test = df_test.drop(0, axis=1)

    # create dataset for lightgbm
    mat_train = lgb.Dataset(X_train, y_train)
    mat_test = lgb.Dataset(X_test, y_test, reference=mat_train)
    return mat_train, mat_test
