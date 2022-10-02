from typing import Dict, List

import torch
from steps.pytorch_trainer import LABEL_MAPPING, load_mobilenetv3_transforms

from zenml.post_execution import get_pipeline
from zenml.steps import BaseParameters, Output, step
from zenml.steps.step_context import StepContext

REVERSE_LABEL_MAPPING = {value: key for key, value in LABEL_MAPPING.items()}
PIPELINE_NAME = "training_pipeline"
PIPELINE_STEP_NAME = "model_trainer"


class PredictionServiceLoaderParameters(BaseParameters):
    training_pipeline_name = "training_pipeline"
    training_pipeline_step_name = "model_trainer"


@step
def prediction_service_loader(
    params: PredictionServiceLoaderParameters, context: StepContext
) -> torch.nn.Module:
    train_run = get_pipeline(params.training_pipeline_name).runs[-1]
    return train_run.get_step(params.training_pipeline_step_name).output.read()


@step
def predictor(
    model: torch.nn.Module,
    images: Dict,
) -> Output(predictions=List):
    preprocess = load_mobilenetv3_transforms()
    preds = []
    for file_name, image in images.items():
        image = preprocess(image)
        image = image.unsqueeze(0)
        pred = model(image)
        pred = pred.squeeze(0).softmax(0)
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
