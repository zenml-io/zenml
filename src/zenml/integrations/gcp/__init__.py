#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from zenml.integrations.integration import Integration
from zenml.utils.source_utils import import_class_by_path


class GcpIntegration(Integration):
    NAME = "gcp"
    REQUIREMENTS = ["gcsfs"]

    @classmethod
    def activate(cls):
        zen_gcs = import_class_by_path(
            "zenml.integrations.gcp.io.gcs_plugin.ZenGCS"
        )

        # TODO: [MEDIUM] we need to implement our own registry
        from tfx.dsl.io import filesystem_registry

        filesystem_registry.DEFAULT_FILESYSTEM_REGISTRY.register(
            zen_gcs, priority=15
        )

        import_class_by_path(
            "zenml.integrations.gcp.artifact_stores.gcp_artifact_store.GCPArtifactStore"
        )
