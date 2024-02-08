#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from pipelines import (
    huggingface_deployment_pipeline,
    inference_pipeline,
    seq_classifier_train_eval_pipeline,
    token_classifier_train_eval_pipeline,
)


@click.command()
@click.option(
    "--task",
    type=click.Choice(
        ["token-classification", "sequence-classification", "deployment"]
    ),
    default="sequence-classification",
    help="Name of the task i.e. token-classification, sequence-classification",
)
def main(task: str):
    if task == "token-classification":
        token_classifier_train_eval_pipeline()

    elif task == "sequence-classification":
        seq_classifier_train_eval_pipeline()

    elif task == "deployment":
        huggingface_deployment_pipeline()
        inference_pipeline()


if __name__ == "__main__":
    main()
