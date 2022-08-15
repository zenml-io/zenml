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
from contextlib import ExitStack as does_not_raise

import numpy as np
import xgboost as xgb

from zenml.integrations.xgboost.materializers.xgboost_dmatrix_materializer import (
    XgboostDMatrixMaterializer,
)
from zenml.steps import step


def test_xgboost_dmatrix_materializer():
    """Tests whether the steps work for the xgboost dmatrix materializer."""

    @step
    def some_step() -> xgb.DMatrix:
        return xgb.DMatrix(np.random.randn(5, 5))

    with does_not_raise():
        some_step().with_return_materializers(XgboostDMatrixMaterializer)()
