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


from zenml.enums import FeatureStoreFlavor, StackComponentType
from zenml.feature_stores.base_feature_store import BaseFeatureStore
from zenml.logger import get_logger
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)

logger = get_logger(__name__)


@register_stack_component_class(
    component_type=StackComponentType.FEATURE_STORE,
    component_flavor=FeatureStoreFlavor.FEAST,
)
class FeastFeatureStore(BaseFeatureStore):
    """Class to interact with the Feast feature store."""

    supports_local_execution: bool = True
    supports_remote_execution: bool = True

    @property
    def flavor(self) -> FeatureStoreFlavor:
        """The feature store flavor."""
        return FeatureStoreFlavor.FEAST
