# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from typing import Optional
from zenml.client import Client
from zenml.logger import get_logger
from zenml.model_registries.base_model_registry import ModelVersionStage

logger = get_logger(__name__)


def promote_in_model_registry(
    latest_version: str, model_name: str, target_env: str, current_version: Optional[str] = None,
):
    """Promote model version in model registry to a given stage.

    Args:
        latest_version: version to be promoted
        current_version: currently promoted version
        model_name: name of the model in registry
        target_env: stage for promotion
    """
    model_registry = Client().active_stack.model_registry
    if model_registry:
        # Why do we need this ???
        # model_registry.configure_mlflow()
        if current_version and latest_version != current_version:
            model_registry.update_model_version(
                name=model_name,
                version=current_version,
                stage=ModelVersionStage(ModelVersionStage.ARCHIVED),
            )
        model_registry.update_model_version(
            name=model_name,
            version=latest_version,
            stage=ModelVersionStage(target_env),
        )
