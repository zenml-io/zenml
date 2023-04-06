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
"""Unit tests for manifest_utils.py."""

from kubernetes.client import V1ObjectMeta, V1Pod

from zenml.integrations.kubernetes.flavors.kubernetes_orchestrator_flavor import (
    KubernetesOrchestratorSettings,
)
from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_pod_manifest,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


def test_build_pod_manifest_metadata():
    """Test that the metadata is correctly set in the manifest."""
    manifest: V1Pod = build_pod_manifest(
        pod_name="test_name",
        run_name="test_run",
        pipeline_name="test_pipeline",
        image_name="test_image",
        command=["test", "command"],
        args=["test", "args"],
        settings=KubernetesOrchestratorSettings(
            pod_settings=KubernetesPodSettings(
                annotations={"blupus_loves": "strawberries"},
            )
        ),
    )
    assert isinstance(manifest, V1Pod)

    metadata = manifest.metadata
    assert isinstance(metadata, V1ObjectMeta)
    assert metadata.name == "test_name"
    assert metadata.labels["run"] == "test_run"
    assert metadata.labels["pipeline"] == "test_pipeline"
    assert metadata.annotations["blupus_loves"] == "strawberries"
