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

import pytest
from kubernetes.client import (
    V1CronJob,
    V1CronJobSpec,
    V1ObjectMeta,
    V1Pod,
    V1PodSpec,
    V1Toleration,
)

from zenml.integrations.kubernetes.orchestrators.manifest_utils import (
    build_cron_job_manifest,
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
        privileged=True,
        pod_settings=KubernetesPodSettings(
            annotations={"blupus_loves": "strawberries"},
        ),
    )
    assert isinstance(manifest, V1Pod)

    metadata = manifest.metadata
    assert isinstance(metadata, V1ObjectMeta)
    assert metadata.name == "test_name"
    assert metadata.labels["run"] == "test_run"
    assert metadata.labels["pipeline"] == "test_pipeline"
    assert metadata.annotations["blupus_loves"] == "strawberries"

    container = manifest.spec.containers[0]
    assert container.security_context.privileged is True


@pytest.fixture
def kubernetes_pod_settings() -> KubernetesPodSettings:
    """build KubernetesPodSettings fixture."""
    pod_settings = KubernetesPodSettings(
        affinity={
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "node.kubernetes.io/name",
                                    "operator": "In",
                                    "values": ["my_powerful_node_group"],
                                }
                            ]
                        }
                    ]
                }
            }
        },
        tolerations=[
            V1Toleration(
                key="node.kubernetes.io/name",
                operator="Equal",
                value="",
                effect="NoSchedule",
            )
        ],
        resources={"requests": {"memory": "2G"}},
    )
    return pod_settings


def test_build_pod_manifest_pod_settings(
    kubernetes_pod_settings: KubernetesPodSettings,
):
    """Test that the pod settings are correctly set in the manifest."""
    manifest: V1Pod = build_pod_manifest(
        pod_name="test_name",
        run_name="test_run",
        pipeline_name="test_pipeline",
        image_name="test_image",
        command=["test", "command"],
        args=["test", "args"],
        privileged=False,
        pod_settings=kubernetes_pod_settings,
    )
    assert isinstance(manifest, V1Pod)
    assert isinstance(manifest.spec, V1PodSpec)
    assert (
        manifest.spec.affinity["nodeAffinity"][
            "requiredDuringSchedulingIgnoredDuringExecution"
        ]["nodeSelectorTerms"][0]["matchExpressions"][0]["key"]
        == "node.kubernetes.io/name"
    )
    assert manifest.spec.tolerations[0]["key"] == "node.kubernetes.io/name"
    assert manifest.spec.containers[0].resources["requests"]["memory"] == "2G"
    assert manifest.spec.containers[0].security_context.privileged is False


def test_build_cron_job_manifest_pod_settings(
    kubernetes_pod_settings: KubernetesPodSettings,
):
    """Test that the pod settings are correctly set in the manifest."""
    manifest: V1CronJob = build_cron_job_manifest(
        cron_expression="* * * * *",
        pod_name="test_name",
        run_name="test_run",
        pipeline_name="test_pipeline",
        image_name="test_image",
        command=["test", "command"],
        args=["test", "args"],
        privileged=False,
        pod_settings=kubernetes_pod_settings,
        service_account_name="test_sa",
    )
    assert isinstance(manifest, V1CronJob)
    assert isinstance(manifest.spec, V1CronJobSpec)
    job_pod_spec = manifest.spec.job_template.spec.template.spec
    assert (
        job_pod_spec.affinity["nodeAffinity"][
            "requiredDuringSchedulingIgnoredDuringExecution"
        ]["nodeSelectorTerms"][0]["matchExpressions"][0]["key"]
        == "node.kubernetes.io/name"
    )
    assert job_pod_spec.tolerations[0]["key"] == "node.kubernetes.io/name"
    assert job_pod_spec.containers[0].resources["requests"]["memory"] == "2G"
    assert job_pod_spec.containers[0].security_context.privileged is False
    assert job_pod_spec.service_account_name == "test_sa"
