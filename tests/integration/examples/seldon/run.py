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
from pipelines.deployment_pipeline import seldon_deployment_pipeline
from pipelines.inference_pipeline import inference_pipeline


@click.command()
@click.option(
    "--model-flavor",
    default="tensorflow",
    type=click.Choice(["tensorflow", "sklearn, pytorch"]),
    help="Flavor of model being trained.",
)
@click.option(
    "--custom-code",
    default=False,
    type=bool,
    help="Whether to test custom code deployment or not.",
)
def main(model_flavor: str = "tensorflow", custom_code: bool = False):
    if model_flavor == "pytorch" and not custom_code:
        raise NotImplementedError(
            "PyTorch flavor is only supported with custom code."
        )
    if model_flavor == "sklearn" and custom_code:
        raise NotImplementedError(
            "sklearn flavor is not supported with custom code."
        )

    seldon_deployment_pipeline(
        custom_code=custom_code,
        model_flavor=model_flavor,
        epochs=5,
        lr=0.003,
        solver="saga",
        penalty="l1",
        penalty_strength=1.0,
        toleration=0.1,
        min_accuracy=0.92,
    )

    inference_pipeline(
        deployment_pipeline_name="seldon_deployment_pipeline",
        custom_code=custom_code,
        model_flavor=model_flavor,
    )


if __name__ == "__main__":
    main()
