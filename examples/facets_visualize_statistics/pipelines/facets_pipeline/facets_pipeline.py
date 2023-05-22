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
from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import FACETS, SKLEARN

docker_settings = DockerSettings(required_integrations=[FACETS, SKLEARN])


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def facets_pipeline(importer, facets_visualization_step):
    """Simple pipeline comparing two datasets using Facets."""
    X_train, X_test, y_train, y_test = importer()
    facets_visualization_step(X_train, X_test)
