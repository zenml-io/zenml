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
import pandas as pd
from neuralprophet import NeuralProphet

from tests.unit.test_general import _test_materializer
from zenml.integrations.neural_prophet.materializers.neural_prophet_materializer import (
    NeuralProphetMaterializer,
)


def test_neural_prophet_booster_materializer(clean_repo):
    """Tests whether the steps work for the Neural Prophet forecaster
    materializer."""
    sample_df = pd.DataFrame(
        {
            "ds": pd.date_range("2018-01-01", periods=10),
            "y": np.random.rand(10),
        }
    )
    model = NeuralProphet(epochs=2, batch_size=37)
    model.fit(sample_df)

    with does_not_raise():
        _test_materializer(
            step_output=model,
            materializer=NeuralProphetMaterializer,
        )

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    forecaster = last_run.steps[-1].output.read()
    assert isinstance(forecaster, NeuralProphet)
    assert forecaster.config_train.epochs == 2
    assert forecaster.config_train.batch_size == 37
