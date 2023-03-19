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
from steps.data_drift_detector import data_drift_detector
from steps.data_loader import data_loader
from steps.data_validator import data_validator
from steps.model_drift_detector import model_drift_detector
from steps.model_validator import model_validator
from steps.trainer import trainer

from zenml.integrations.deepchecks.visualizers import DeepchecksVisualizer
from zenml.logger import get_logger

logger = get_logger(__name__)


if __name__ == "__main__":
    pipeline_instance = data_validation_pipeline(
        data_loader=data_loader(),
        trainer=trainer(),
        data_validator=data_validator,
        model_validator=model_validator,
        data_drift_detector=data_drift_detector,
        model_drift_detector=model_drift_detector,
    )
    pipeline_instance.run()

    last_run = pipeline_instance.get_runs()[0]
    data_val_step = last_run.get_step(step="data_validator")
    model_val_step = last_run.get_step(step="model_validator")
    data_drift_step = last_run.get_step(step="data_drift_detector")
    model_drift_step = last_run.get_step(step="model_drift_detector")
    DeepchecksVisualizer().visualize(data_val_step)
    DeepchecksVisualizer().visualize(model_val_step)
    DeepchecksVisualizer().visualize(data_drift_step)
    DeepchecksVisualizer().visualize(model_drift_step)
