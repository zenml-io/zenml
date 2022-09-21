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
from contextlib import ExitStack as does_not_raise
from pathlib import Path

import lightgbm as lgb
import pytest

from zenml.integrations.lightgbm.materializers.lightgbm_booster_materializer import (
    LightGBMBoosterMaterializer,
)
from zenml.steps import step


@pytest.fixture
def empty_model_file() -> Path:
    """Fixture to get an empty model.txt file"""

    with tempfile.NamedTemporaryFile() as tmp:
        yield tmp.name


def test_lightgbm_booster_materializer(empty_model_file):
    """Tests whether the steps work for the lightgbm booster materializer."""

    @step
    def some_step() -> lgb.Booster:
        return lgb.Booster(model_file=empty_model_file)

    with does_not_raise():
        some_step().with_return_materializers(LightGBMBoosterMaterializer)()
