import tensorflow as tf
from datasets import DatasetDict
from steps.configuration import HuggingfaceParameters
from transformers import (
    DataCollatorForTokenClassification,
    PreTrainedTokenizerBase,
    TFPreTrainedModel,
)

from zenml import step


@step
def token_evaluator(
    params: HuggingfaceParameters,
    model: TFPreTrainedModel,
    tokenized_datasets: DatasetDict,
    tokenizer: PreTrainedTokenizerBase,
) -> float:
    """Evaluate trained model on validation set."""
    # Needs to recompile because we are reloading model for evaluation
    model.compile(optimizer=tf.keras.optimizers.Adam())

    # Convert into tf dataset format
    validation_set = tokenized_datasets["validation"].to_tf_dataset(
        columns=["attention_mask", "input_ids", "labels"],
        shuffle=False,
        batch_size=params.batch_size,
        collate_fn=DataCollatorForTokenClassification(
            tokenizer, return_tensors="tf"
        ),
    )

    # Calculate loss
    if params.dummy_run:
        test_loss = model.evaluate(validation_set.take(10), verbose=1)
    else:
        test_loss = model.evaluate(validation_set, verbose=1)
    return test_loss
