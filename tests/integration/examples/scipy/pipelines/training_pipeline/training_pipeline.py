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
from steps import importer, predictor, trainer, vectorizer

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import PANDAS, SKLEARN

docker_settings = DockerSettings(required_integrations=[SKLEARN, PANDAS])


@pipeline(enable_cache=True, settings={"docker": docker_settings})
def scipy_example_pipeline():
    X_train, X_test, y_train, y_test = importer()
    vec_transformer, X_train_vec, X_test_vec = vectorizer(X_train, X_test)
    model = trainer(X_train_vec, y_train)
    predictor(vec_transformer, model, X_test)
