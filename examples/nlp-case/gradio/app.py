# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
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
from os.path import dirname
from typing import Optional

import click
import numpy as np
from transformers import AutoModelForSequenceClassification, AutoTokenizer

import gradio as gr


@click.command()
@click.option(
    "--tokenizer_name_or_path",
    default="tokenizer",
    help="Name or the path of the tokenizer.",
)
@click.option(
    "--model_name_or_path",
    default="model",
    help="Name or the path of the model.",
)
@click.option(
    "--labels",
    default="Negative,Positive",
    help="Comma-separated list of labels.",
)
@click.option(
    "--title",
    default="ZenML NLP Use-Case",
    help="Title of the Gradio interface.",
)
@click.option(
    "--description",
    default="Text Classification - Sentiment Analysis - ZenML - Gradio",
    help="Description of the Gradio interface.",
)
@click.option(
    "--interpretation",
    default="default",
    help="Interpretation mode for the Gradio interface.",
)
@click.option(
    "--examples",
    default="This is an awesome journey, I love it!",
    help="An example to show in the Gradio interface.",
)
def sentiment_analysis(
    tokenizer_name_or_path: Optional[str],
    model_name_or_path: Optional[str],
    labels: Optional[str],
    title: Optional[str],
    description: Optional[str],
    interpretation: Optional[str],
    examples: Optional[str],
):
    """Launches a Gradio interface for sentiment analysis.

    This function launches a Gradio interface for text-classification.
    It loads a model and a tokenizer from the provided paths and uses
    them to predict the sentiment of the input text.

    Args:
        tokenizer_name_or_path (str): Name or the path of the tokenizer.
        model_name_or_path (str): Name or the path of the model.
        labels (str): Comma-separated list of labels.
        title (str): Title of the Gradio interface.
        description (str): Description of the Gradio interface.
        interpretation (str): Interpretation mode for the Gradio interface.
        examples (str): Comma-separated list of examples to show in the Gradio interface.
    """
    labels = labels.split(",")
    examples = [examples]

    def preprocess(text: str) -> str:
        """Preprocesses the text.

        Args:
            text (str): Input text.

        Returns:
            str: Preprocessed text.
        """
        new_text = []
        for t in text.split(" "):
            t = "@user" if t.startswith("@") and len(t) > 1 else t
            t = "http" if t.startswith("http") else t
            new_text.append(t)
        return " ".join(new_text)

    def softmax(x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum(axis=0)

    def analyze_text(text):
        model_path = f"{dirname(__file__)}/{model_name_or_path}/"
        print(f"Loading model from {model_path}")
        tokenizer_path = f"{dirname(__file__)}/{tokenizer_name_or_path}/"
        print(f"Loading tokenizer from {tokenizer_path}")
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)

        text = preprocess(text)
        encoded_input = tokenizer(text, return_tensors="pt")
        output = model(**encoded_input)
        scores_ = output[0][0].detach().numpy()
        scores_ = softmax(scores_)

        scores = {l: float(s) for (l, s) in zip(labels, scores_)}
        return scores

    demo = gr.Interface(
        fn=analyze_text,
        inputs=[
            gr.TextArea("Write your text or tweet here", label="Analyze Text")
        ],
        outputs=["label"],
        title=title,
        description=description,
        interpretation=interpretation,
        examples=examples,
    )

    demo.launch(share=True, debug=True)


if __name__ == "__main__":
    sentiment_analysis()
