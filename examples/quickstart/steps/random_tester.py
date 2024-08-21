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
import torch
from datasets import Dataset
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
)

from zenml import log_model_metadata, step
from zenml.logger import get_logger

from .data_loader import PROMPT

logger = get_logger(__name__)


@step
def model_tester(
    model: T5ForConditionalGeneration,
    tokenized_test_dataset: Dataset,
    tokenizer: T5Tokenizer
) -> None:
    """Test the model on some generated Old English-style sentences."""

    model.eval()  # Set the model to evaluation mode

    test_collection = {}

    for index in range(len(tokenized_test_dataset)):
        input_ids = tokenized_test_dataset[index]["input_ids"]

        # Convert input_ids to a tensor and add a batch dimension
        input_ids_tensor = torch.tensor(input_ids).unsqueeze(0)

        with torch.no_grad():
            outputs = model.generate(
                input_ids_tensor,
                max_length=128,
                num_return_sequences=1,
                no_repeat_ngram_size=2,
                top_k=50,
                top_p=0.95,
                temperature=0.7,
            )

        decoded_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Decode the input_ids to get the original sentence
        original_sentence = tokenizer.decode(input_ids[0], skip_special_tokens=True)
        sentence_without_prompt = original_sentence.strip(PROMPT)

        test_collection[f"Prompt {index}"] = {
            sentence_without_prompt: decoded_output
        }

    log_model_metadata({"Example Prompts": test_collection})
