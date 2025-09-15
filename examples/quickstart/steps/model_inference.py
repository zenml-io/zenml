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
from typing import Annotated, Dict, Optional, Tuple

import torch
from datasets import Dataset
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
)

from zenml import get_step_context, step
from zenml.logger import get_logger

from .data_loader import PROMPT

logger = get_logger(__name__)


def load_models(
    model_name: str = "model", tokenizer_name: str = "tokenizer"
) -> Tuple[T5ForConditionalGeneration, T5Tokenizer]:
    """Load the model from the pipeline."""
    from zenml.client import Client

    client = Client()

    model: Optional[T5ForConditionalGeneration] = client.get_artifact_version(
        model_name
    ).load()
    if model is None:
        raise ValueError("Model artifact not found")

    model.eval()  # Set the model to evaluation mode

    tokenizer: Optional[T5Tokenizer] = client.get_artifact_version(
        tokenizer_name
    ).load()
    if tokenizer is None:
        raise ValueError("Tokenizer artifact not found")

    return model, tokenizer


@step
def load_inference_data(
    input: str,
) -> Annotated[Dataset, "inference_dataset"]:
    """Load and prepare the data for inference."""

    def read_data_from_string(data: str) -> dict[str, list[str]]:
        return {"input": data.splitlines()}

    # Fetch and process the data
    data = read_data_from_string(input)

    print(f"Data: {data}")

    # Convert to Dataset
    dataset = Dataset.from_dict(data)
    print(f"Dataset: {dataset}")
    return dataset


@step
def tokenize_inference_data(
    dataset: Dataset,
) -> Annotated[Dataset, "tokenized_dataset"]:
    """Tokenize the dataset."""
    step_context = get_step_context()
    pipeline_state = step_context.pipeline_state

    if pipeline_state is None:
        raise RuntimeError("Pipeline state is not set")

    tokenizer: T5Tokenizer = pipeline_state[1]

    def tokenize_function(examples):
        model_inputs = tokenizer(
            examples["input"],
            max_length=128,
            truncation=True,
            padding="max_length",
        )
        if "target" in examples:
            labels = tokenizer(
                examples["target"],
                max_length=128,
                truncation=True,
                padding="max_length",
            )
            model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    dataset = dataset.map(tokenize_function, batched=True)
    print(f"Tokenized dataset: {dataset}")
    return dataset


@step
def call_model(
    tokenized_dataset: Dataset,
) -> Dict[str, Dict[str, str]]:
    """Test the model on some generated Old English-style sentences."""
    step_context = get_step_context()
    pipeline_state = step_context.pipeline_state
    if pipeline_state is None:
        raise RuntimeError("Pipeline state is not set")

    model: T5ForConditionalGeneration = pipeline_state[0]
    tokenizer: T5Tokenizer = pipeline_state[1]

    test_collection = {}

    for index in range(len(tokenized_dataset)):
        input_ids = tokenized_dataset[index]["input_ids"]

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
        original_sentence = tokenizer.decode(
            input_ids[0], skip_special_tokens=True
        )
        sentence_without_prompt = original_sentence.strip(PROMPT)

        test_collection[f"Prompt {index}"] = {
            sentence_without_prompt: decoded_output
        }

        print(f"Prompt {index}: {sentence_without_prompt} -> {decoded_output}")

    return test_collection
