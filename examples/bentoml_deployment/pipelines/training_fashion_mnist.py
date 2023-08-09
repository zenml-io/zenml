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

from steps.bento_builder import bento_builder
from steps.deployer import bentoml_model_deployer
from steps.deployment_trigger_step import (
    deployment_trigger,
)
from steps.evaluators import evaluator
from steps.importers import importer_mnist
from steps.trainers import trainer

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import BENTOML, PYTORCH

docker_settings = DockerSettings(required_integrations=[PYTORCH, BENTOML])


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def training_fashion_mnist():
    """Train a model and deploy it with BentoML."""
    train_dataloader, test_dataloader = importer_mnist()
    model = trainer(train_dataloader)
    accuracy = evaluator(test_dataloader=test_dataloader, model=model)
    decision = deployment_trigger(accuracy=accuracy, min_accuracy=0.80)
    bento = bento_builder(model=model)
    bentoml_model_deployer(bento=bento, deploy_decision=decision)
