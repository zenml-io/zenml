#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from typing import Dict, List

import torch
from steps.pytorch_trainer import LABEL_MAPPING
from transformers import AutoTokenizer

from zenml.post_execution import get_pipeline
from zenml.steps import BaseParameters, Output, step
from zenml.steps.step_context import StepContext

REVERSE_LABEL_MAPPING = {value: key for key, value in LABEL_MAPPING.items()}
PIPELINE_NAME = "training_pipeline"
PIPELINE_STEP_NAME = "model_trainer"


class PredictionServiceLoaderParameters(BaseParameters):
    training_pipeline_name = PIPELINE_NAME
    training_pipeline_step_name = PIPELINE_STEP_NAME


@step
def prediction_service_loader(
    params: PredictionServiceLoaderParameters, context: StepContext
) -> (
    torch.nn.Module
):  # transformers.pipelines.text_classification.TextClassificationPipeline:
    train_run = get_pipeline(params.training_pipeline_name).runs[0]
    return train_run.get_step(params.training_pipeline_step_name).output.read()


@step(enable_cache=True)
def predictor(
    model: torch.nn.Module,  # transformers.pipelines.text_classification.TextClassificationPipeline,
    texts: Dict,
) -> Output(predictions=List):
    preds = []
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    for file_name, text in texts.items():
        tokenized_text = tokenizer(
            " ".join(text.split(" ")[:300]), return_tensors="pt"
        )
        pred = model(**tokenized_text)
        pred = pred.logits[0].softmax(0)
        class_id = pred.argmax().item()
        class_name = REVERSE_LABEL_MAPPING[class_id]
        label_studio_output = {
            "filename": file_name,
            "result": [
                {
                    "value": {"choices": [class_name]},
                    "from_name": "choice",
                    "to_name": "image",
                    "type": "choices",
                    "origin": "manual",
                },
            ],
        }
        preds.append(label_studio_output)
    return preds
