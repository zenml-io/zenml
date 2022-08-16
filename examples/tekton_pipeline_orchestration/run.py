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
from pipelines.mnist_pipeline import mnist_pipeline
from steps.evaluators import evaluator
from steps.importers import importer
from steps.normalizers import normalizer
from steps.trainers import TrainerConfig, trainer


@click.command()
@click.option("--epochs", default=5, help="Number of epochs for training")
@click.option("--lr", default=0.001, help="Learning rate for training")
def main(epochs: int, lr: float):
    """Run the mnist example pipeline"""
    # Run the pipeline
    pipeline_instance = mnist_pipeline(
        importer=importer(),
        normalizer=normalizer(),
        trainer=trainer(config=TrainerConfig(epochs=epochs, lr=lr)),
        evaluator=evaluator(),
    )
    pipeline_instance.run()


if __name__ == "__main__":
    main()
