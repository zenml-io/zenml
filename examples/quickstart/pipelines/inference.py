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
from steps.model_inference import (
    call_model,
    load_inference_data,
    load_models,
    tokenize_inference_data,
)

from zenml import pipeline
from zenml.logger import get_logger

logger = get_logger(__name__)


@pipeline(
    enable_cache=False,
    on_init=load_models,
)
def english_translation_inference(
    input: str = "",
):
    """Define a pipeline that connects the steps."""
    inference_dataset = load_inference_data(input=input)
    tokenized_dataset = tokenize_inference_data(
        dataset=inference_dataset,
    )
    return call_model(
        tokenized_dataset=tokenized_dataset,
    )
