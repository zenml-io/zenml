#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from datasets import DatasetDict, load_dataset

from zenml import step


@step
def data_importer(dataset_name: str) -> DatasetDict:
    """Load dataset using huggingface datasets."""
    datasets = load_dataset(dataset_name, trust_remote_code=True)
    print("Sample Example :", datasets["train"][7])
    return datasets
