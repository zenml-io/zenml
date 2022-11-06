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

from pipelines.bentoml_fashion_mnist_pipeline import bentoml_fashion_mnist_pipeline
from steps.bento_builder import bento_builder
from steps.deployer import bentoml_model_deployer
from steps.deployment_trigger_step import (
    DeploymentTriggerParameters,
    deployment_trigger,
)
from steps.evaluators import evaluator
from steps.importers import importer_mnist
from steps.trainers import trainer

if __name__ == "__main__":
    bentoml_fashion_mnist_pipeline(
        importer=importer_mnist(),
        trainer=trainer(),
        evaluator=evaluator(),
        deployment_trigger=deployment_trigger(
            params=DeploymentTriggerParameters(
                min_accuracy=0.80,
            )
        ),
        bento_builder=bento_builder,
        deployer=bentoml_model_deployer,
    ).run()
