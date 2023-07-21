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

from pipelines.mnist_pipeline import mnist_pipeline

from zenml.integrations.tensorboard.visualizers import (
    stop_tensorboard_server,
    visualize_tensorboard,
)


def main():
    """Run the mnist example pipeline."""
    mnist_pipeline()
    visualize_tensorboard(
        pipeline_name="mnist_pipeline",
        step_name="trainer",
    )
    stop_tensorboard_server(
        pipeline_name="mnist_pipeline",
        step_name="trainer",
    )


if __name__ == "__main__":
    main()
