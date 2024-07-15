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

import pandas as pd
from datasets import Dataset

from tests.unit.test_general import _test_materializer
from zenml.integrations.huggingface.materializers.huggingface_datasets_materializer import (
    HFDatasetMaterializer,
    extract_repo_name,
)


def test_huggingface_datasets_materializer(clean_client):
    """Tests whether the steps work for the Huggingface Datasets materializer."""
    sample_dataframe = pd.DataFrame([1, 2, 3])
    dataset = Dataset.from_pandas(sample_dataframe)
    dataset = _test_materializer(
        step_output=dataset,
        materializer_class=HFDatasetMaterializer,
        expected_metadata_size=7,
    )

    assert dataset.data.shape == (3, 1)
    data = dataset.data.to_pydict()
    assert "0" in data.keys()
    assert [1, 2, 3] in data.values()


def test_extract_repo_name():
    """Tests whether the extract_repo_name function works correctly."""
    # Test valid URL
    url = "hf://datasets/nyu-mll/glue@bcdcba79d07bc864c1c254ccfcedcce55bcc9a8c/mrpc/train-00000-of-00001.parquet"
    assert extract_repo_name(url) == "nyu-mll/glue"

    # Test valid URL with different dataset
    url = "hf://datasets/huggingface/dataset-name@123456/subset/file.parquet"
    assert extract_repo_name(url) == "huggingface/dataset-name"

    # Test URL without file
    url = "hf://datasets/org/repo@commit"
    assert extract_repo_name(url) == "org/repo"

    # Test URL with extra parts
    url = "hf://datasets/org/repo/extra/parts@commit/file.parquet"
    assert extract_repo_name(url) == "org/repo"

    # Test invalid URL (too short)
    url = "hf://datasets/org"
    assert extract_repo_name(url) is None

    # Test invalid URL format
    url = "https://huggingface.co/datasets/org/repo"
    assert extract_repo_name(url) is None

    # Test empty string
    assert extract_repo_name("") is None

    # Test None input
    assert extract_repo_name(None) is None


def test_extract_repo_name_edge_cases():
    """Tests edge cases for the extract_repo_name function."""
    # Test URL with no '@' symbol
    url = "hf://datasets/org/repo/file.parquet"
    assert extract_repo_name(url) == "org/repo"

    # Test URL with multiple '@' symbols
    url = "hf://datasets/org/repo@commit@extra/file.parquet"
    assert extract_repo_name(url) == "org/repo"

    # Test URL with special characters in repo name
    url = "hf://datasets/org-name/repo_name-123@commit/file.parquet"
    assert extract_repo_name(url) == "org-name/repo_name-123"


def test_extract_repo_name_exceptions():
    """Tests exception handling in the extract_repo_name function."""
    # Test with non-string input
    assert extract_repo_name(123) is None

    # Test with list input
    assert extract_repo_name(["not", "a", "string"]) is None

    # Test with dict input
    assert extract_repo_name({"not": "a string"}) is None
