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
from datasets import DatasetDict
from steps.configuration import HuggingfaceParameters
from transformers import PreTrainedTokenizerBase

from zenml import step


@step
def token_classification_tokenization(
    params: HuggingfaceParameters,
    tokenizer: PreTrainedTokenizerBase,
    datasets: DatasetDict,
) -> DatasetDict:
    """Tokenizer dataset into tokens and then convert into encoded ids."""

    def tokenize_and_align_labels(examples):
        tokenized_inputs = tokenizer(
            examples[params.text_column],
            truncation=True,
            is_split_into_words=True,
        )

        labels = []
        for i, label in enumerate(examples[params.label_column]):
            word_ids = tokenized_inputs.word_ids(batch_index=i)
            previous_word_idx = None
            label_ids = []
            for word_idx in word_ids:
                # Special tokens have a word id that is None. We set the label
                # to -100 so they are automatically ignored in the loss
                # function.
                if word_idx is None:
                    label_ids.append(-100)
                # We set the label for the first token of each word.
                elif word_idx != previous_word_idx:
                    label_ids.append(label[word_idx])
                # For the other tokens in a word, we set the label to either the
                #  current label or -100, depending on the label_all_tokens
                #  flag.
                else:
                    label_ids.append(
                        label[word_idx] if params.label_all_tokens else -100
                    )
                previous_word_idx = word_idx

            labels.append(label_ids)

        tokenized_inputs["labels"] = labels
        return tokenized_inputs

    tokenized_datasets = datasets.map(tokenize_and_align_labels, batched=True)
    return tokenized_datasets
