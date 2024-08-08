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

    def read_data(file_path):
        inputs = []
        targets = []

        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                old, modern = line.strip().split("|")
                inputs.append(
                    f"{PROMPT}{old}"
                )
                targets.append(modern)

        return {"input": inputs, "target": targets}

    # Assuming your file is named 'translations.txt'
    data = read_data("translations.txt")
    test_data = read_data("test-translations.txt")

    return Dataset.from_dict(data), Dataset.from_dict(test_data)
