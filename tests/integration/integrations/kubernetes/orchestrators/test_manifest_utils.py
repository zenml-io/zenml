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
    V1JobSpec,
    V1JobTemplateSpec,
    V1ObjectMeta,
    V1Pod,
    V1PodSpec,
    V1PodTemplateSpec,
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
def minimal_job_template() -> V1JobTemplateSpec:
    """Build a minimal V1JobTemplateSpec fixture for CronJob tests."""
    pod_template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(name="test-pod"),
        spec=V1PodSpec(containers=[], restart_policy="Never"),
    )
    return V1JobTemplateSpec(
        metadata=V1ObjectMeta(name="test-job"),
        spec=V1JobSpec(template=pod_template),
    )


def test_build_cron_job_manifest_with_cronjob_spec_fields(
    minimal_job_template: V1JobTemplateSpec,
):
    """Test that concurrency_policy and starting_deadline_seconds are set."""
    manifest: V1CronJob = build_cron_job_manifest(
        job_template=minimal_job_template,
        cron_expression="0 2 * * *",
        successful_jobs_history_limit=2,
        failed_jobs_history_limit=1,
        concurrency_policy="Forbid",
        starting_deadline_seconds=20,
    )
    assert isinstance(manifest, V1CronJob)
    assert manifest.spec.schedule == "0 2 * * *"
    assert manifest.spec.concurrency_policy == "Forbid"
    assert manifest.spec.starting_deadline_seconds == 20
    assert manifest.spec.successful_jobs_history_limit == 2
    assert manifest.spec.failed_jobs_history_limit == 1


def test_build_cron_job_manifest_defaults_none(
    minimal_job_template: V1JobTemplateSpec,
):
    """Test that omitting new fields preserves backwards-compatible behavior."""
    manifest: V1CronJob = build_cron_job_manifest(
        job_template=minimal_job_template,
        cron_expression="0 0 * * *",
    )
    assert isinstance(manifest, V1CronJob)
    assert manifest.spec.schedule == "0 0 * * *"
    assert manifest.spec.concurrency_policy is None
    assert manifest.spec.starting_deadline_seconds is None
    assert manifest.spec.successful_jobs_history_limit is None
    assert manifest.spec.failed_jobs_history_limit is None
