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

from typing import Optional
from uuid import UUID

from steps import load_data, tokenize_data, train_model, evaluate_model, test_random_sentences

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)

@pipeline
def english_translation_pipeline(model_type: str):
    """Define a pipeline that connects the steps."""
    dataset = load_data()
    tokenized_dataset = tokenize_data(dataset)
    model_path = train_model(tokenized_dataset)
    evaluate_model(model_path, tokenized_dataset)
    test_random_sentences(model_path)
