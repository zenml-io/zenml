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
import random
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)

old_english_words = [
    "Thrice",
    "brinded",
    "hath",
    "mew'd",
    "Tongue",
    "adder's",
    "fork",
    "raven",
    "hoarse",
    "Unsex",
    "fardels",
    "Yond",
    "lean",
    "hungry",
    "Zounds",
    "pox",
    "Alack",
    "perfumes",
    "Arabia",
    "sweeten",
    "wit's end",
    "Ay",
    "rub",
    "Bacon-fed",
    "knaves",
    "Beggars",
    "mounted",
    "Bestride",
    "Colossus",
    "Brave",
    "toil",
    "trouble",
    "yonder",
    "pricking",
    "thumbs",
    "wicked",
    "Havoc",
    "bootless",
    "cloistered",
    "newt",
    "frog",
    "Fie",
    "foh",
    "fum",
    "Flaming",
    "youth",
    "Foregone",
    "Frailty",
    "cradle",
    "grave",
    "Gild",
    "lily",
    "Hark",
    "Hie",
    "thee",
    "hence",
    "Howl",
    "wink",
    "dagger",
    "idiot",
    "green-eyed",
    "monster",
    "parlous",
    "Methinks",
    "doth",
    "protest",
    "bedfellows",
    "kingdom",
    "horse",
    "stirring",
    "flesh",
    "melt",
    "breach",
    "villain",
    "damned",
    "spot",
    "Plague",
    "Valiant",
    "Primrose",
    "slaughter",
    "budge",
    "alarum-bell",
    "eyeballs",
    "heavens",
    "Strumpet",
    "fortune",
    "Tartar's",
    "bow",
]

@step
def test_random_sentences(model: T5ForConditionalGeneration, tokenizer: T5Tokenizer) -> None:
    """Test the model on some generated Old English-style sentences."""

    model.eval()  # Set the model to evaluation mode

    def generate_old_english_sentence():
        sentence_length = random.randint(5, 10)
        return " ".join(
            random.choice(old_english_words) for _ in range(sentence_length)
        )

    test_sentences = [generate_old_english_sentence() for _ in range(5)]

    for sentence in test_sentences:
        input_text = f"translate Old English to Modern English: {sentence}"
        input_ids = tokenizer(
            input_text,
            return_tensors="pt",
            max_length=128,
            truncation=True,
            padding="max_length",
        ).input_ids

        with torch.no_grad():
            outputs = model.generate(
                input_ids,
                max_length=128,
                num_return_sequences=1,
                no_repeat_ngram_size=2,
                top_k=50,
                top_p=0.95,
                temperature=0.7,
            )

        decoded_output = tokenizer.decode(outputs[0], skip_special_tokens=True)

        print(f"Generated Old English: {sentence}")
        print(f"Model Translation: {decoded_output}")
        print()