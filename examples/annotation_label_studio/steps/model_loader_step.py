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

from fastai.learner import Learner

from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.steps import step

logger = get_logger(__name__)


@step
def model_loader() -> Learner:
    repo = Repository(skip_repository_check=True)
    trainer_output = (
        repo.get_pipeline("training_pipeline")
        .runs[-1]
        .get_step("model_trainer")
        .output
    )
    breakpoint()
