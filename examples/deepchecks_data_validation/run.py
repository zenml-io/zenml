#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from pipelines.data_validation import data_validation_pipeline
from steps.data_loader import data_loader
from steps.data_validator import data_validator
from steps.post_validation import post_validation
from steps.trainer import trainer

from zenml.integrations.deepchecks.visualizers import DeepchecksVisualizer
from zenml.logger import get_logger
from zenml.repository import Repository

logger = get_logger(__name__)


if __name__ == "__main__":
    pipeline = data_validation_pipeline(
        data_loader=data_loader(),
        trainer=trainer(),
        data_validator=data_validator(),
        post_validation=post_validation(),
    )
    pipeline.run()

    repo = Repository()
    pipeline = repo.get_pipeline(pipeline_name="data_validation_pipeline")
    last_run = pipeline.runs[-1]
    data_val_step = last_run.get_step(name="data_validator")
    DeepchecksVisualizer().visualize(data_val_step)
