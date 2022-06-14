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
"""Implementation of Kubernetes metadata store."""

from typing import ClassVar

from kubernetes import client, config

from zenml.integrations.kubernetes import KUBERNETES_METADATA_STORE_FLAVOR
from zenml.integrations.kubernetes.orchestrators.kube_utils import (
    create_mysql_deployment,
    create_namespace,
    make_core_v1_api,
)
from zenml.logger import get_logger
from zenml.metadata_stores.mysql_metadata_store import MySQLMetadataStore

logger = get_logger(__name__)


class KubernetesMetadataStore(MySQLMetadataStore):
    """Kubernetes metadata store (MySQL database deployed in the cluster).

    Attributes:
        kubernetes_namespace: Name of the kubernetes namespace.
            Defaults to "default".
        deployment_name: Name of the deployment (and corresponding service/pod)
            that will be created when calling `provision()`.
            Defaults to "mysql".
        storage_capacity: Storage capacity of the metadata store.
            Defaults to "10Gi" (=10GB).
    """

    kubernetes_namespace: str = "default"
    deployment_name: str = "mysql"
    storage_capacity: str = "10Gi"

    FLAVOR: ClassVar[str] = KUBERNETES_METADATA_STORE_FLAVOR

    @property
    def deployment_exists(self) -> bool:
        """Check whether a mysql deployment exists in the cluster.

        Returns:
            Whether a mysql deployment exists in the cluster.
        """
        config.load_kube_config()
        v1 = client.AppsV1Api()
        resp = v1.list_namespaced_deployment(
            namespace=self.kubernetes_namespace
        )
        for i in resp.items:
            if i.metadata.name == self.deployment_name:
                return True
        return False

    @property
    def is_provisioned(self) -> bool:
        """If the component provisioned resources to run.

        Checks whether the required MySQL deployment exists.

        Returns:
            True if the component provisioned resources to run.
        """
        return super().is_provisioned and self.deployment_exists

    def provision(self) -> None:
        """Provision the metadata store.

        Creates a deployment with a MySQL database running in it.
        """
        logger.info("Provisioning Kubernetes MySQL metadata store...")
        core_api = make_core_v1_api()
        create_namespace(core_api=core_api, namespace=self.kubernetes_namespace)
        create_mysql_deployment(
            core_api=core_api,
            namespace=self.kubernetes_namespace,
            storage_capacity=self.storage_capacity,
            deployment_name=self.deployment_name,
            service_name=self.deployment_name,
        )
