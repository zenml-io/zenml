#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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
"""Shared Docker settings for the MLflow example pipelines."""

import mlflow

from zenml.config import DockerSettings
from zenml.integrations.constants import MLFLOW, SKLEARN

# Pin MLflow inside the orchestrator image to the version installed on the
# client. The example uses ZenML's local MLflow backend, a SQLite database in
# the artifact store that the orchestrator container and the test process
# both open. A newer MLflow in the container migrates that database to a
# schema revision the client cannot read ("Detected out-of-date database
# schema"), which is what happened when MLflow 3.16.0 was released while the
# client environment still resolved 3.15.2.
docker_settings = DockerSettings(
    required_integrations=[MLFLOW, SKLEARN],
    requirements=["scikit-image", f"mlflow=={mlflow.__version__}"],
)
