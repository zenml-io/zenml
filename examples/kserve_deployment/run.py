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
import click
from pipelines.kserve_sklearn_pipeline import kserve_sklearn_pipeline
from steps.deployment_trigger import DeploymentTriggerConfig, deployment_trigger
from steps.model_deployer import custom_kserve_sklearn_deployer
from steps.sklearn_evaluator import evaluator
from steps.sklearn_importer import importer
from steps.sklearn_trainer import trainer


@click.command()
@click.option(
    "--min-accuracy",
    default=0.85,
    help="Minimum accuracy required to deploy the model (default: 0.85)",
)
def main(
    min_accuracy: float,
):
    """Run the mnist example pipeline"""
    deployment_pipeline = kserve_sklearn_pipeline(
        importer=importer(),
        trainer=trainer(),
        evaluator=evaluator(),
        deployment_trigger=deployment_trigger(
            config=DeploymentTriggerConfig(
                min_accuracy=min_accuracy,
            )
        ),
        model_deployer=custom_kserve_sklearn_deployer,
    )
    deployment_pipeline.run()


if __name__ == "__main__":
    main()
