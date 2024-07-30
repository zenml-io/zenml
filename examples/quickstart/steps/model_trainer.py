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
    T5Tokenizer,
    T5ForConditionalGeneration,
    Trainer,
    TrainingArguments,
)
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)

@step
def train_model(tokenized_dataset: Dataset) -> Annotated[str, "model_path"]:
    """Train the model and return the path to the saved model."""
    # Check if CUDA is available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model = T5ForConditionalGeneration.from_pretrained("t5-small").to(device)
    tokenizer = T5Tokenizer.from_pretrained("t5-small")

    training_args = TrainingArguments(
        output_dir="./results",
        num_train_epochs=3,
        per_device_train_batch_size=8,
        logging_dir="./logs",
        logging_steps=10,
        save_steps=50,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset,
    )

    trainer.train()

    # Save the model
    model_path = "./final_model"
    trainer.save_model(model_path)

    # Basic check
    test_input = tokenizer(
        "translate Old English to Modern English: Hark, what light through yonder window breaks?",
        return_tensors="pt",
    ).to(device)
    with torch.no_grad():
        test_output = model.generate(**test_input)
    print(
        "Test translation:", tokenizer.decode(test_output[0], skip_special_tokens=True)
    )

    print("Model training completed and saved.")
    return model_path
