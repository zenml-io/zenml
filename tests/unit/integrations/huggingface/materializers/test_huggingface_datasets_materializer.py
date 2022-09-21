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

import pandas as pd
from datasets import Dataset

from tests.unit.test_general import _test_materializer
from zenml.integrations.huggingface.materializers.huggingface_datasets_materializer import (
    HFDatasetMaterializer,
)


def test_huggingface_datasets_materializer(clean_repo):
    """Tests whether the steps work for the Huggingface Datasets
    materializer."""
    sample_dataframe = pd.DataFrame([1, 2, 3])
    dataset = Dataset.from_pandas(sample_dataframe)
    with does_not_raise():
        _test_materializer(
            step_output=dataset,
            materializer=HFDatasetMaterializer,
        )

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    dataset = last_run.steps[-1].output.read()
    assert isinstance(dataset, Dataset)
    assert dataset.data.shape == (3, 1)
    data = dataset.data.to_pydict()
    assert "0" in data.keys()
    assert [1, 2, 3] in data.values()
