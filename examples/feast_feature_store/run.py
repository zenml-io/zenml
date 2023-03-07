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

from pipelines import feast_pipeline
from steps.getter.get_features_step import get_features
from steps.printer.printer_step import feature_printer

from zenml.logger import get_logger

logger = get_logger(__name__)


if __name__ == "__main__":
    pipeline_instance = feast_pipeline(
        get_features=get_features,
        feature_printer=feature_printer(),
    )

    pipeline_instance.run()

    last_run = pipeline_instance.get_runs()[0]
    historical_features_step = last_run.get_step(step="feature_printer")
    print("HISTORICAL FEATURES:")
    print(historical_features_step.output.read())
