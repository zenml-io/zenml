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
    V1ObjectMeta,
    V1Pod,
    V1PodSpec,
    V1Toleration,
)

from zenml.integrations.kubernetes.manifest_utils import (
    build_cron_job_manifest,
    build_pod_manifest,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings


def test_build_pod_manifest_metadata():
    """Test that the metadata is correctly set in the manifest."""
    manifest: V1Pod = build_pod_manifest(
        pod_name="test_name",
        image_name="test_image",
        command=["test", "command"],
        args=["test", "args"],
        privileged=True,
        pod_settings=KubernetesPodSettings(
            annotations={"blupus_loves": "strawberries"},
        ),
        labels={"run": "test-run", "pipeline": "test-pipeline"},
    )
    assert isinstance(manifest, V1Pod)

    metadata = manifest.metadata
    assert isinstance(metadata, V1ObjectMeta)
    assert metadata.name == "test_name"
    assert metadata.labels["run"] == "test-run"
    assert metadata.labels["pipeline"] == "test-pipeline"
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


@pytest.fixture
def sample_job_template():
    """Create a minimal V1JobTemplateSpec for CronJob tests."""
    from kubernetes.client import (
        V1Container,
        V1JobSpec,
        V1JobTemplateSpec,
        V1PodTemplateSpec,
    )

    pod_template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(name="test-job"),
        spec=V1PodSpec(
            containers=[V1Container(name="main", image="test:latest")],
            restart_policy="Never",
        ),
    )
    return V1JobTemplateSpec(
        metadata=V1ObjectMeta(name="test-job"),
        spec=V1JobSpec(template=pod_template),
    )


def test_build_cron_job_manifest_concurrency_policy(sample_job_template):
    """Test that concurrency_policy is set on the CronJob spec."""
    manifest = build_cron_job_manifest(
        job_template=sample_job_template,
        cron_expression="0 * * * *",
        concurrency_policy="Forbid",
    )
    assert manifest.spec.concurrency_policy == "Forbid"


def test_build_cron_job_manifest_starting_deadline_seconds(
    sample_job_template,
):
    """Test that starting_deadline_seconds is set on the CronJob spec."""
    manifest = build_cron_job_manifest(
        job_template=sample_job_template,
        cron_expression="0 * * * *",
        starting_deadline_seconds=300,
    )
    assert manifest.spec.starting_deadline_seconds == 300


def test_build_cron_job_manifest_all_cron_fields(sample_job_template):
    """Test that all CronJob-specific fields are correctly set together."""
    manifest = build_cron_job_manifest(
        job_template=sample_job_template,
        cron_expression="*/5 * * * *",
        successful_jobs_history_limit=3,
        failed_jobs_history_limit=1,
        concurrency_policy="Replace",
        starting_deadline_seconds=600,
    )
    assert manifest.spec.schedule == "*/5 * * * *"
    assert manifest.spec.successful_jobs_history_limit == 3
    assert manifest.spec.failed_jobs_history_limit == 1
    assert manifest.spec.concurrency_policy == "Replace"
    assert manifest.spec.starting_deadline_seconds == 600


def test_build_cron_job_manifest_defaults_none(sample_job_template):
    """Test that new fields default to None when not specified."""
    manifest = build_cron_job_manifest(
        job_template=sample_job_template,
        cron_expression="0 0 * * *",
    )
    assert manifest.spec.concurrency_policy is None
    assert manifest.spec.starting_deadline_seconds is None
