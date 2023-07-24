import numpy as np
import pandas as pd
import requests
from config import ModelMetadata

from zenml.integrations.mlflow.services import MLFlowDeploymentService
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    mlflow_model_registry_deployer_step,
)


def predict_as_dict(dataset: pd.DataFrame, model_version: str):
    deployment: MLFlowDeploymentService = mlflow_model_registry_deployer_step(
        registry_model_name=ModelMetadata.mlflow_model_name,
        registry_model_version=model_version,
    )

    # TODO: code below doesn't work, as I would expect
    # throws 500 and returns following:
    #
    # Failed to parse data as TF serving input. Ensure that the input is a
    # valid JSON-formatted string that conforms to the request body for TF
    # serving\'s Predict API as documented at
    # https://www.tensorflow.org/tfx/serving/api_rest#request_format_2
    # CODE vvv
    # tmp_deployment.predict(dataset_tst.drop(columns=["target"]).to_numpy())
    # CODE ^^^
    response = requests.post(
        deployment.endpoint.prediction_url,
        json={"instances": dataset.to_dict("records")},
    )
    response.raise_for_status()
    return np.array(response.json()["predictions"])
