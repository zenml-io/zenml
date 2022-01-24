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
import os
from typing import Union

from kubernetes import config as k8s_config
from ml_metadata.proto import metadata_store_pb2

from zenml.enums import MetadataStoreFlavor, StackComponentType
from zenml.metadata_stores import MySQLMetadataStore
from zenml.stack.stack_component_class_registry import (
    register_stack_component_class,
)


def inside_kfp_pod() -> bool:
    """Returns if the current python process is running inside a KFP Pod."""
    if "KFP_POD_NAME" not in os.environ:
        return False

    try:
        k8s_config.load_incluster_config()
        return True
    except k8s_config.ConfigException:
        return False


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

    def get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Return tfx metadata config for the kubeflow metadata store."""
        if inside_kfp_pod():
            connection_config = metadata_store_pb2.MetadataStoreClientConfig()
            connection_config.host = os.environ["METADATA_GRPC_SERVICE_HOST"]
            connection_config.port = int(
                os.environ["METADATA_GRPC_SERVICE_PORT"]
            )
            return connection_config
        else:
            return super().get_tfx_metadata_config()
