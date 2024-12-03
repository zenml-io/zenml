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

from typing import Optional, Tuple

import mlflow
from datasets import DatasetDict
from transformers import (
    AutoModelForSequenceClassification,
    DataCollatorWithPadding,
    PreTrainedModel,
    PreTrainedTokenizerBase,
    Trainer,
    TrainingArguments,
)
from typing_extensions import Annotated
from utils.misc import compute_metrics

from zenml import ArtifactConfig, log_metadata, step
from zenml.client import Client
from zenml.integrations.mlflow.experiment_trackers import (
    MLFlowExperimentTracker,
)
from zenml.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Get experiment tracker
experiment_tracker = Client().active_stack.experiment_tracker

# Check if experiment tracker is set and is of type MLFlowExperimentTracker
if not experiment_tracker or not isinstance(
    experiment_tracker, MLFlowExperimentTracker
):
    raise RuntimeError(
        "Your active stack needs to contain a MLFlow experiment tracker for "
        "this example to work."
    )


@step(experiment_tracker=experiment_tracker.name)
def model_trainer(
    tokenized_dataset: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
    num_labels: Optional[int] = None,
    train_batch_size: Optional[int] = 16,
    num_epochs: Optional[int] = 3,
    learning_rate: Optional[float] = 2e-5,
    load_best_model_at_end: Optional[bool] = True,
    eval_batch_size: Optional[int] = 16,
    weight_decay: Optional[float] = 0.01,
    mlflow_model_name: Optional[str] = "sentiment_analysis",
) -> Tuple[
    Annotated[
        PreTrainedModel, ArtifactConfig(name="model", is_model_artifact=True)
    ],
    Annotated[
        PreTrainedTokenizerBase,
        ArtifactConfig(name="tokenizer", is_model_artifact=True),
    ],
]:
    """
    Configure and train a model on the training dataset.

    This step takes in a dataset artifact previously loaded and pre-processed by
    other steps in your pipeline, then configures and trains a model on it. The
    model is then returned as a step output artifact.

    Model training steps should have caching disabled if they are not deterministic
    (i.e. if the model training involve some random processes like initializing
    weights or shuffling data that are not controlled by setting a fixed random seed).


    Args:
        tokenized_dataset: The tokenized dataset.
        tokenizer: The tokenizer.
        num_labels: The number of labels.
        train_batch_size: Training batch size.
        num_epochs: Number of epochs.
        learning_rate: Learning rate.
        load_best_model_at_end: Whether to load the best model at the end of training.
        eval_batch_size: Evaluation batch size.
        weight_decay: Weight decay.
        mlflow_model_name: The name of the model in MLFlow.

    Returns:
        The trained model and tokenizer.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Select the appropriate datasets based on the dataset type
    train_dataset = tokenized_dataset["train"]
    eval_dataset = tokenized_dataset["validation"]

    # Initialize data collator
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # Set the number of labels
    num_labels = len(train_dataset.unique("labels")) or num_labels

    # Set the logging steps
    logging_steps = len(train_dataset) // train_batch_size

    # Initialize training arguments
    training_args = TrainingArguments(
        output_dir="zenml_artifact",
        learning_rate=learning_rate,
        per_device_train_batch_size=train_batch_size,
        per_device_eval_batch_size=eval_batch_size,
        num_train_epochs=num_epochs,
        weight_decay=weight_decay,
        evaluation_strategy="steps",
        save_strategy="steps",
        save_steps=1000,
        eval_steps=100,
        logging_steps=logging_steps,
        save_total_limit=5,
        report_to="mlflow",
        load_best_model_at_end=load_best_model_at_end,
    )
    logger.info(f"Training arguments: {training_args}")

    # Load the model
    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased", num_labels=num_labels
    )

    # Enable autologging
    mlflow.transformers.autolog()

    # Initialize the trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
        data_collator=data_collator,
    )

    # Train and evaluate the model
    trainer.train()
    eval_results = trainer.evaluate(metric_key_prefix="")

    # Log the evaluation results in model control plane
    log_metadata(
        metadata={"metrics": eval_results},
        artifact_name="model",
        infer_artifact=True,
    )
    ### YOUR CODE ENDS HERE ###

    return model, tokenizer
