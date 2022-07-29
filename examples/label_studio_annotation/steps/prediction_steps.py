from typing import Dict, List

import torch
from steps.pytorch_trainer import LABEL_MAPPING, load_mobilenetv3_transforms

from zenml.steps import Output, step
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_context import StepContext

REVERSE_LABEL_MAPPING = {value: key for key, value in LABEL_MAPPING.items()}
PIPELINE_NAME = "training_pipeline"
PIPELINE_STEP_NAME = "model_trainer"  # TODO: change to "model_deployer"


# @step(enable_cache=False)
# def prediction_service_loader() -> BaseService:
#     """Load the model service of our train_evaluate_deploy_pipeline."""
#     repo = Repository(skip_repository_check=True)
#     model_deployer = repo.active_stack.model_deployer
#     services = model_deployer.find_model_server(
#         pipeline_name=PIPELINE_NAME,
#         pipeline_step_name=PIPELINE_STEP_NAME,
#         running=True,
#     )
#     service = services[0]
#     return service


# @step
# def predictor(
#     service: BaseService,
#     data: np.ndarray,  # TODO
# ) -> Output(predictions=list):
#     """Run a inference request against a prediction service"""
#     service.start(timeout=10)  # should be a NOP if already started
#     # TODO: iterate over images, convert predictions to label studio format
#     prediction = service.predict(data)
#     prediction = prediction.argmax(axis=-1)
#     print(f"Prediction is: {[prediction.tolist()]}")
#     return [prediction.tolist()]


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
