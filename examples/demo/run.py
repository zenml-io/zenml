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
from pipelines.registry_pipelines.registry_inference_pipeline import (
        mlflow_registry_inference_pipeline,
)
from pipelines.registry_pipelines.registry_training_pipeline import (
        mlflow_registry_training_pipeline,
)


@click.command()
def main(type: str) -> None:
        mlflow_registry_training_pipeline()
        mlflow_registry_inference_pipeline()


if __name__ == "__main__":
    main()
