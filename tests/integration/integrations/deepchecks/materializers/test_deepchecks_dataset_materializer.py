#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Unit tests for Deepchecks dataset materializer."""

import sys
from contextlib import ExitStack as does_not_raise

import pytest

from tests.unit.test_general import _test_materializer


@pytest.mark.skipif(
    sys.version_info.minor >= 12,
    reason="The deepchecks integrations is not yet supported on 3.12.",
)
def test_deepchecks_dataset_materializer(clean_client):
    """Test the Deepchecks dataset materializer."""

    import pandas as pd
    from deepchecks.tabular import Dataset

    from zenml.integrations.deepchecks.materializers.deepchecks_dataset_materializer import (
        DeepchecksDatasetMaterializer,
    )

    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}, index=["a", "b", "c"])
    deepchecks_dataset = Dataset(
        df,
        label="B",
    )
    with does_not_raise():
        _test_materializer(
            step_output=deepchecks_dataset,
            materializer_class=DeepchecksDatasetMaterializer,
            assert_visualization_exists=True,
        )
