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

from zenml.config import DockerSettings
from zenml.integrations.constants import FACETS, SKLEARN
from zenml.pipelines import pipeline

docker_settings = DockerSettings(required_integrations=[SKLEARN, FACETS])


@pipeline(enable_cache=False, settings={"docker": docker_settings})
def kubernetes_example_pipeline(importer, trainer, evaluator, skew_comparison):
    """data loading -> train -> test with skew comparison in parallel."""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)
    skew_comparison(X_train, X_test)
