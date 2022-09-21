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

from tests.unit.test_general import _test_materializer
from zenml.integrations.xgboost.materializers.xgboost_dmatrix_materializer import (
    XgboostDMatrixMaterializer,
)


def test_xgboost_dmatrix_materializer(clean_repo):
    """Tests whether the steps work for the XGBoost Booster materializer."""
    with does_not_raise():
        _test_materializer(
            step_output=xgb.DMatrix(np.random.randn(5, 5)),
            materializer=XgboostDMatrixMaterializer,
        )

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    dmatrix = last_run.steps[-1].output.read()
    assert isinstance(dmatrix, xgb.DMatrix)
    assert dmatrix.num_row() == 5
    assert dmatrix.num_col() == 5
