#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
from pipeline import (
    TrainerConfig,
    evaluator,
    importer,
    mnist_pipeline,
    normalizer,
    trainer,
)

from zenml.integrations.tensorflow.visualizers import (
    stop_tensorboard_server,
    visualize_tensorboard,
)


@click.command()
@click.option("--epochs", default=5, help="Number of epochs for training")
@click.option("--lr", default=0.001, help="Learning rate for training")
@click.option(
    "--stop-tensorboard",
    is_flag=True,
    default=False,
    help="Stop the Tensorboard server",
)
def main(epochs: int, lr: float, stop_tensorboard: bool):
    """Run the mnist example pipeline"""

    if stop_tensorboard:
        stop_tensorboard_server(
            pipeline_name="mnist_pipeline",
            step_name="trainer",
        )
        return

    # Run the pipeline
    p = mnist_pipeline(
        importer=importer(),
        normalizer=normalizer(),
        trainer=trainer(config=TrainerConfig(epochs=epochs, lr=lr)),
        evaluator=evaluator(),
    )
    p.run()

    visualize_tensorboard(
        pipeline_name="mnist_pipeline",
        step_name="trainer",
    )


if __name__ == "__main__":
    main()
