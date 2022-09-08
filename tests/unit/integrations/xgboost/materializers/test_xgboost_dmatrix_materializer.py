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
from zenml.pipelines import pipeline
from zenml.steps import step


def test_xgboost_dmatrix_materializer(clean_repo):
    """Tests whether the steps work for the XGBoost Booster materializer."""

    @step
    def read_dmatrix() -> xgb.DMatrix:
        """Reads and materializes a XGBoost DMatrix object."""
        return xgb.DMatrix(np.random.randn(5, 5))

    @pipeline
    def test_pipeline(read_dmatrix) -> None:
        """Tests the XGBoost DMatrix object materializer."""
        read_dmatrix()

    with does_not_raise():
        test_pipeline(
            read_dmatrix=read_dmatrix().with_return_materializers(
                XgboostDMatrixMaterializer
            )
        ).run()

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    booster = last_run.steps[-1].output.read()
    assert isinstance(booster, xgb.DMatrix)
