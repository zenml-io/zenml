# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from typing import Tuple, Annotated

from datasets import Dataset
from fastapi import requests

from zenml import step
from zenml.logger import get_logger

from materializers.dataset_materializer import DatasetMaterializer

logger = get_logger(__name__)

PROMPT = ""  # In case you want to also use a prompt you can set it here


@step(output_materializers=DatasetMaterializer)
def load_data() -> Tuple[
    Annotated[Dataset, "dataset"],
    Annotated[Dataset, "test_dataset"],
]:
    """Load and prepare the dataset."""

    def read_data_from_url(url):
        inputs = []
        targets = []

        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad responses

        for line in response.text.splitlines():
            old, modern = line.strip().split("|")
            inputs.append(f"{PROMPT}{old}")
            targets.append(modern)

        return {"input": inputs, "target": targets}

    # URLs for the data files
    train_url = "https://storage.googleapis.com/zenml-public-bucket/quickstart-files/translations.txt"
    test_url = "https://storage.googleapis.com/zenml-public-bucket/quickstart-files/test-translations.txt"

    # Fetch and process the data
    data = read_data_from_url(train_url)
    test_data = read_data_from_url(test_url)

    return Dataset.from_dict(data), Dataset.from_dict(test_data)
