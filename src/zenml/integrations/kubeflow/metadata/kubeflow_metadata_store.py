#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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


from zenml.enums import MetadataStoreFlavor, StackComponentType
from zenml.metadata_stores import MySQLMetadataStore
from zenml.new_core.stack_component_class_registry import (
    register_stack_component_class,
)


@register_stack_component_class(
    component_type=StackComponentType.METADATA_STORE,
    component_flavor=MetadataStoreFlavor.KUBEFLOW,
)
class KubeflowMetadataStore(MySQLMetadataStore):
    """Kubeflow MySQL backend for ZenML metadata store."""

    host: str = "127.0.0.1"
    port: int = 3306
    database: str = "metadb"
    username: str = "root"
    password: str = ""

    @property
    def flavor(self) -> MetadataStoreFlavor:
        """The metadata store flavor."""
        return MetadataStoreFlavor.KUBEFLOW
