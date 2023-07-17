from pipelines.deploy_and_predict import deploy_and_predict
from pipelines.train_and_register_model import (
    train_and_register_model_pipeline,
)

from zenml.client import Client

if __name__ == "__main__":
    train_and_register_model_pipeline()
    best_model_test_accuracy = (
        Client()
        .get_pipeline("train_and_register_model_pipeline")
        .last_successful_run.steps["best_model_selector"]
        .outputs["best_model_test_acc"]
        .load()
    )

    if best_model_test_accuracy > 0.7:
        deploy_and_predict()
