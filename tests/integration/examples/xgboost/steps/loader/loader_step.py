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
from typing import Tuple

import requests
import xgboost as xgb
from typing_extensions import Annotated

from zenml import step

TRAIN_SET_RAW = (
    "https://raw.githubusercontent.com/dmlc/xgboost/master/demo"
    "/data/agaricus.txt.train"
)

TEST_SET_RAW = (
    "https://raw.githubusercontent.com/dmlc/xgboost/master/demo"
    "/data/agaricus.txt.test"
)


@step
def data_loader() -> (
    Tuple[
        Annotated[xgb.DMatrix, "mat_train"], Annotated[xgb.DMatrix, "mat_test"]
    ]
):
    """Retrieves the data from the demo directory of the XGBoost repo."""
    # Write data to temporary files to load it with `xgb.DMatrix`.
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".html", encoding="utf-8"
    ) as f:
        f.write(requests.get(TRAIN_SET_RAW, timeout=13).text)
        mat_train = xgb.DMatrix(f.name + "?format=libsvm")

    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".html", encoding="utf-8"
    ) as f:
        f.write(requests.get(TEST_SET_RAW, timeout=13).text)
        mat_test = xgb.DMatrix(f.name + "?format=libsvm")

    return mat_train, mat_test
