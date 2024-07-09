#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import click
from pipelines.deployment_pipelines.deployment_inference_pipeline import (
    mlflow_deployment_inference_pipeline,
)
from pipelines.deployment_pipelines.deployment_training_pipeline import (
    mlflow_train_deploy_pipeline,
)
from pipelines.registry_pipelines.registry_inference_pipeline import (
    mlflow_registry_inference_pipeline,
)
from pipelines.registry_pipelines.registry_training_pipeline import (
    mlflow_registry_training_pipeline,
)
from pipelines.tracking_pipeline.tracking_pipeline import (
    mlflow_tracking_pipeline,
)


@click.command()
@click.option(
    "--type",
    default="tracking",
    help="The type of MLflow example to run.",
    type=click.Choice(["tracking", "registry", "deployment"]),
)
def main(type: str) -> None:
    if type == "tracking":
        mlflow_tracking_pipeline()
    elif type == "registry":
        mlflow_registry_training_pipeline()
        #mlflow_registry_inference_pipeline()
    elif type == "deployment":
        mlflow_train_deploy_pipeline()
        mlflow_deployment_inference_pipeline()
    else:
        raise NotImplementedError(
            f"MLflow example type {type} not implemented."
        )


if __name__ == "__main__":
    main()
