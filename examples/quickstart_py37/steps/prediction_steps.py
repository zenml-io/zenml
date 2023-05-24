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

import pandas as pd

from zenml.client import Client
from zenml.services import BaseService
from zenml.steps import Output, step


@step(enable_cache=False)
def prediction_service_loader() -> BaseService:
    """Load the model service of our train_evaluate_deploy_pipeline."""
    client = Client()
    model_deployer = client.active_stack.model_deployer
    services = model_deployer.find_model_server(
        pipeline_name="training_pipeline",
        pipeline_step_name="model_deployer",
        running=False,
    )
    service = services[0]
    return service


@step
def predictor(
    service: BaseService,
    data: pd.DataFrame,
) -> Output(predictions=list):
    """Run a inference request against a prediction service."""
    service.start(timeout=60)  # should be a NOP if already started
    prediction = service.predict(data.to_numpy())
    prediction = prediction.argmax(axis=-1)
    print(f"Prediction is: {[prediction.tolist()]}")
    return [prediction.tolist()]
