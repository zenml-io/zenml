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


@click.command()
@click.option("--epochs", default=5, help="Number of epochs for training")
@click.option("--lr", default=0.001, help="Learning rate for training")
def main(epochs: int, lr: float):
    """Run the mnist example pipeline."""
    mnist_pipeline(epochs=epochs, lr=lr)


if __name__ == "__main__":
    main()
