"""TensorFlow dataset helpers for HuggingFace token classification."""

from typing import Iterator

import tensorflow as tf
from datasets import Dataset
from transformers import (
    DataCollatorForTokenClassification,
    PreTrainedTokenizerBase,
)

TOKEN_CLASSIFICATION_COLUMNS = ("attention_mask", "input_ids", "labels")


def create_tf_token_classification_dataset(
    dataset: Dataset,
    tokenizer: PreTrainedTokenizerBase,
    batch_size: int,
    shuffle: bool = False,
) -> tf.data.Dataset:
    """Create a TensorFlow dataset for token classification examples."""
    collator = DataCollatorForTokenClassification(
        tokenizer, return_tensors="tf"
    )

    def batch_generator() -> Iterator[dict[str, tf.Tensor]]:
        indices = list(range(len(dataset)))
        if shuffle:
            indices = tf.random.shuffle(indices).numpy().tolist()

        for start in range(0, len(indices), batch_size):
            batch_indices = indices[start : start + batch_size]
            examples = [
                {
                    column: dataset[index][column]
                    for column in TOKEN_CLASSIFICATION_COLUMNS
                }
                for index in batch_indices
            ]
            yield collator(examples)

    return tf.data.Dataset.from_generator(
        batch_generator,
        output_signature={
            column: tf.TensorSpec(shape=(None, None), dtype=tf.int64)
            for column in TOKEN_CLASSIFICATION_COLUMNS
        },
    )
