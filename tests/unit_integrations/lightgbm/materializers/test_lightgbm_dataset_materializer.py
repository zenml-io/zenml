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

import lightgbm as lgb

from zenml.integrations.lightgbm.materializers.lightgbm_dataset_materializer import (
    LightGBMDatasetMaterializer,
)
from zenml.steps import step


def test_lightgbm_dataset_materializer():
    """Tests whether the steps work for the lightgbm dataset materializer."""

    @step
    def some_step() -> lgb.Dataset:
        return lgb.Dataset(data=[[1, 2, 3]], label=[1])

    with does_not_raise():
        some_step().with_return_materializers(LightGBMDatasetMaterializer)()
