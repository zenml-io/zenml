#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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


import os

from steps import (
    importer_step,
    split_step,
    statistics_step,
    trainer_step,
    transformer_step,
)

from zenml import pipeline
from zenml.config import DockerSettings

docker_settings = DockerSettings(
    requirements=["zenml"], parent_image=os.getenv("BASE_IMAGE_NAME")
)


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def spark_pipeline():
    dataset = importer_step(path=os.getenv("SPARK_DEMO_DATASET"))
    statistics_step(dataset)
    train, test, evaluation = split_step(dataset)
    train_xf, _, _ = transformer_step(train)
    trainer_step(train_xf)
