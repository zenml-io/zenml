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

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import BENTOML, PYTORCH

docker_settings = DockerSettings(required_integrations=[PYTORCH, BENTOML])


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def training_fashion_mnist(
    importer,
    trainer,
    evaluator,
    deployment_trigger,
    bento_builder,
    deployer,
):
    """Link all the steps and artifacts together."""
    train_dataloader, test_dataloader = importer()
    model = trainer(train_dataloader)
    accuracy = evaluator(test_dataloader=test_dataloader, model=model)
    decision = deployment_trigger(accuracy=accuracy)
    bento = bento_builder(model=model)
    deployer(deploy_decision=decision, bento=bento)
