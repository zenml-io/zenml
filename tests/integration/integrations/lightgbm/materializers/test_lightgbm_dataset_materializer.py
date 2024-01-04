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

import platform

import lightgbm as lgb
import numpy as np
import pytest

from tests.unit.test_general import _test_materializer
from zenml.integrations.lightgbm.materializers.lightgbm_dataset_materializer import (
    LightGBMDatasetMaterializer,
)


@pytest.mark.skipif(
    platform.system() == "Darwin",
    reason="https://github.com/microsoft/LightGBM/issues/4229",
)
def test_lightgbm_dataset_materializer():
    """Tests whether the steps work for the lightgbm dataset materializer."""
    ds = lgb.Dataset(data=np.array([[1, 2, 3]]), label=np.array([1]))
    _test_materializer(
        step_output=ds,
        materializer_class=LightGBMDatasetMaterializer,
        expected_metadata_size=2,
    )
