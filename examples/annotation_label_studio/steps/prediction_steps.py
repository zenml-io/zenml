from typing import List

import numpy as np
import torch
from torchvision import models, transforms

from zenml.repository import Repository
from zenml.services import BaseService
from zenml.steps import Output, step
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_context import StepContext

PIPELINE_NAME = "training_pipeline"
PIPELINE_STEP_NAME = "model_trainer"  # TODO: change to "model_deployer"


@step(enable_cache=False)
def prediction_service_loader() -> BaseService:
    """Load the model service of our train_evaluate_deploy_pipeline."""
    repo = Repository(skip_repository_check=True)
    model_deployer = repo.active_stack.model_deployer
    services = model_deployer.find_model_server(
        pipeline_name=PIPELINE_NAME,
        pipeline_step_name=PIPELINE_STEP_NAME,
        running=True,
    )
    service = services[0]
    return service


@step
def predictor(
    service: BaseService,
    data: np.ndarray,  # TODO
) -> Output(predictions=list):
    """Run a inference request against a prediction service"""
    service.start(timeout=10)  # should be a NOP if already started
    # TODO: iterate over images, convert predictions to label studio format
    prediction = service.predict(data)
    prediction = prediction.argmax(axis=-1)
    print(f"Prediction is: {[prediction.tolist()]}")
    return [prediction.tolist()]


class PredictionServiceLoaderConfig(BaseStepConfig):
    training_pipeline_name = "training_pipeline"
    training_pipeline_step_name = "model_trainer"  # TODO: "model_deployer"?


@step
def prediction_service_loader(
    config: PredictionServiceLoaderConfig, context: StepContext
) -> torch.nn.Module:
    train_run = context.metadata_store.get_pipeline(
        config.training_pipeline_name
    ).runs[-1]
    return train_run.get_step(config.training_pipeline_step_name).output.read()


@step
def predictor(
    model: torch.nn.Module,
    images: np.ndarray,
    image_names: List[str],
) -> Output(predictions=List):

    # TODO: get the preprocessing from the training step
    # -> torchvision integration
    models.MobileNet_V3_Small_Weights.DEFAULT
    preprocess = transforms.Compose(
        [
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )

    preds = []
    for file_name, image in zip(image_names, images):
        image = preprocess(image)
        image = image.unsqueeze(0)
        pred = model(image)
        pred = pred.squeeze(0).softmax(0)
        class_id = pred.argmax().item()
        class_name = {0: "aria", 1: "not_aria"}[class_id]
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
