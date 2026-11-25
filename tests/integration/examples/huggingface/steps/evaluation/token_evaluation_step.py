"""Evaluation step for the HuggingFace token classification example."""

import tensorflow as tf
from datasets import DatasetDict
from steps.tf_dataset import create_tf_token_classification_dataset
from transformers import PreTrainedTokenizerBase, TFPreTrainedModel

from zenml import step


@step
def token_evaluator(
    model: TFPreTrainedModel,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
    dummy_run: bool = True,
    batch_size: int = 8,
) -> float:
    """Evaluate trained model on validation set."""
    # Needs to recompile because we are reloading model for evaluation
    model.compile(optimizer=tf.keras.optimizers.Adam())

    validation_set = create_tf_token_classification_dataset(
        dataset=tokenized_datasets["validation"],
        tokenizer=tokenizer,
        batch_size=batch_size,
        shuffle=False,
    )

    # Calculate loss
    if dummy_run:
        test_loss = model.evaluate(validation_set.take(10), verbose=1)
    else:
        test_loss = model.evaluate(validation_set, verbose=1)
    return test_loss
