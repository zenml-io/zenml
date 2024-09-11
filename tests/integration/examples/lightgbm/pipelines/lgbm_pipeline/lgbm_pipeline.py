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
from steps.data_loader.data_loader_step import data_loader
from steps.predictor.predictor_step import predictor
from steps.trainer.trainer_step import trainer

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import LIGHTGBM, PANDAS

docker_settings = DockerSettings(
    required_integrations=[LIGHTGBM, PANDAS], apt_packages=["libgomp1"]
)


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def lgbm_pipeline():
    """Links all the steps together in a pipeline."""
    mat_train, mat_test = data_loader()
    model = trainer(mat_train, mat_test)
    predictor(model)
