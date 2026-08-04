#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Unit tests for multi-pod command steps on the K8s step operator."""

from typing import Dict, Optional, Tuple
from unittest.mock import MagicMock, PropertyMock, patch
from uuid import uuid4

import pytest
from kubernetes import client as k8s_client

from zenml.enums import StackComponentType
from zenml.integrations.kubernetes.constants import MULTI_POD_MAIN_PORT
from zenml.integrations.kubernetes.flavors import (
    KubernetesStepOperatorConfig,
    KubernetesStepOperatorSettings,
)
from zenml.integrations.kubernetes.kube_utils import (
    multi_pod_environment,
    multi_pod_job_name,
)
from zenml.integrations.kubernetes.manifest_utils import (
    build_headless_service_manifest,
    build_job_manifest,
)
from zenml.integrations.kubernetes.step_operators.kubernetes_step_operator import (
    KubernetesStepOperator,
)


def _job() -> k8s_client.V1Job:
    """Build a minimal job manifest.

    Returns:
        The job manifest.
    """
    return k8s_client.V1Job(
        metadata=k8s_client.V1ObjectMeta(
            name="job-x", uid="uid-1", labels={"step_name": "train"}
        ),
        spec=k8s_client.V1JobSpec(
            parallelism=1,
            template=k8s_client.V1PodTemplateSpec(
                spec=k8s_client.V1PodSpec(containers=[])
            ),
        ),
    )


class TestJobName:
    def test_letter_prefix_for_leading_digit(self) -> None:
        # Service names must be RFC 1035 labels starting with a letter.
        assert multi_pod_job_name("0abc-train", pod_count=2) == "j0abc-train"

    def test_letter_start_unchanged(self) -> None:
        assert multi_pod_job_name("abc-train", pod_count=2) == "abc-train"

    def test_truncation_leaves_room_for_pod_hostname_index(self) -> None:
        name = multi_pod_job_name("a" * 63, pod_count=10)
        assert len(name) <= 61

    def test_no_trailing_dash_after_truncation(self) -> None:
        name = multi_pod_job_name("a" * 60 + "-bc", pod_count=2)
        assert not name.endswith("-")


class TestMultiNodeEnvironment:
    def test_multi_pod(self) -> None:
        env = multi_pod_environment(
            job_name="job-x", namespace="zenml", pod_count=3
        )
        assert env["ZENML_KUBERNETES_POD_COUNT"] == "3"
        assert (
            env["ZENML_KUBERNETES_MAIN_ADDRESS"] == "job-x-0.job-x.zenml.svc"
        )
        assert env["ZENML_KUBERNETES_MAIN_PORT"] == str(MULTI_POD_MAIN_PORT)
        # Kubernetes injects the rank into the pods of an indexed job.
        assert "JOB_COMPLETION_INDEX" not in env


class TestManifests:
    def test_indexed_completion(self) -> None:
        job = build_job_manifest(
            job_name="job-x",
            pod_template=k8s_client.V1PodTemplateSpec(
                spec=k8s_client.V1PodSpec(containers=[])
            ),
            pod_count=3,
        )
        assert job.spec.parallelism == 3
        assert job.spec.completions == 3
        assert job.spec.completion_mode == "Indexed"
        # Pod hostname + service subdomain give stable per-pod DNS.
        assert job.spec.template.spec.subdomain == "job-x"

    def test_headless_service_owned_by_job(self) -> None:
        service = build_headless_service_manifest(_job())
        assert service.spec.cluster_ip == "None"
        assert service.spec.selector == {"job-name": "job-x"}
        assert service.spec.ports[0].port == MULTI_POD_MAIN_PORT
        assert service.spec.publish_not_ready_addresses is True
        owner = service.metadata.owner_references[0]
        assert owner.kind == "Job"
        assert owner.name == "job-x"
        assert owner.uid == "uid-1"


def _make_info(command: Optional[list] = None) -> MagicMock:
    """Build a step run info mock.

    Args:
        command: The step command, None for a regular step.

    Returns:
        The step run info mock.
    """
    info = MagicMock()
    info.pipeline_step_name = "train"
    info.run_id = uuid4()
    info.run_name = "run"
    info.step_run_id = uuid4()
    info.pipeline.name = "pipe"
    info.snapshot.project_id = uuid4()
    info.get_image.return_value = "image:latest"
    info.config.command = command
    return info


def _submit(
    info: MagicMock,
    pod_count: int = 1,
    batch_api: Optional[MagicMock] = None,
    core_api: Optional[MagicMock] = None,
) -> Tuple[MagicMock, MagicMock]:
    """Run submit with mocked Kubernetes APIs.

    Args:
        info: The step run info mock.
        pod_count: The pod count to set in the step settings.
        batch_api: The batch API mock.
        core_api: The core API mock.

    Returns:
        The batch and core API mocks.
    """

    def _create_job(
        namespace: str, body: k8s_client.V1Job
    ) -> k8s_client.V1Job:
        body.metadata.uid = "uid-1"
        return body

    batch_api = batch_api or MagicMock()
    batch_api.create_namespaced_job.side_effect = _create_job
    core_api = core_api or MagicMock()

    operator = KubernetesStepOperator(
        name="k8s",
        id=uuid4(),
        config=KubernetesStepOperatorConfig(),
        flavor="kubernetes",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created="2026-01-01T00:00:00",
        updated="2026-01-01T00:00:00",
    )

    with (
        patch.object(
            KubernetesStepOperator,
            "_k8s_batch_api",
            new_callable=PropertyMock,
            return_value=batch_api,
        ),
        patch.object(
            KubernetesStepOperator,
            "_k8s_core_api",
            new_callable=PropertyMock,
            return_value=core_api,
        ),
        patch.object(
            KubernetesStepOperator,
            "get_settings",
            return_value=KubernetesStepOperatorSettings(pod_count=pod_count),
        ),
    ):
        operator.submit(
            info=info,
            entrypoint_command=["bash", "-lc", "torchrun train.py"],
            environment={"USER_VAR": "1"},
        )

    return batch_api, core_api


def _container_env(job_manifest: k8s_client.V1Job) -> Dict[str, str]:
    """Extract the container environment from a job manifest.

    Args:
        job_manifest: The job manifest.

    Returns:
        The container environment variables.
    """
    container = job_manifest.spec.template.spec.containers[0]
    return {var.name: var.value for var in container.env}


class TestSubmit:
    def test_multi_pod_command_step(self) -> None:
        batch_api, core_api = _submit(
            _make_info(command=["bash", "-lc", "torchrun train.py"]),
            pod_count=2,
        )

        job_manifest = batch_api.create_namespaced_job.call_args.kwargs["body"]
        job_name = job_manifest.metadata.name
        assert job_name[0].isalpha()
        assert len(job_name) <= 61
        assert job_manifest.spec.completion_mode == "Indexed"
        assert job_manifest.spec.parallelism == 2
        assert job_manifest.spec.completions == 2
        assert job_manifest.spec.template.spec.subdomain == job_name

        env = _container_env(job_manifest)
        assert env["USER_VAR"] == "1"
        assert env["ZENML_KUBERNETES_POD_COUNT"] == "2"
        assert job_name in env["ZENML_KUBERNETES_MAIN_ADDRESS"]
        assert "JOB_COMPLETION_INDEX" not in env

        service = core_api.create_namespaced_service.call_args.kwargs["body"]
        assert service.metadata.name == job_name

    def test_single_pod_command_step(self) -> None:
        batch_api, core_api = _submit(
            _make_info(command=["bash", "-lc", "torchrun train.py"])
        )

        job_manifest = batch_api.create_namespaced_job.call_args.kwargs["body"]
        assert job_manifest.spec.completion_mode is None

        env = _container_env(job_manifest)
        assert "ZENML_KUBERNETES_MAIN_ADDRESS" not in env

        core_api.create_namespaced_service.assert_not_called()

    def test_single_pod_regular_step(self) -> None:
        batch_api, core_api = _submit(_make_info())

        job_manifest = batch_api.create_namespaced_job.call_args.kwargs["body"]
        env = _container_env(job_manifest)
        assert "ZENML_KUBERNETES_MAIN_ADDRESS" not in env

        core_api.create_namespaced_service.assert_not_called()

    def test_multi_pod_regular_step_refused(self) -> None:
        with pytest.raises(RuntimeError, match="not a command step"):
            _submit(_make_info(), pod_count=2)

    def test_job_deleted_when_service_creation_fails(self) -> None:
        info = _make_info(command=["bash", "-lc", "torchrun train.py"])
        batch_api = MagicMock()
        core_api = MagicMock()
        core_api.create_namespaced_service.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            _submit(info, pod_count=2, batch_api=batch_api, core_api=core_api)

        batch_api.delete_namespaced_job.assert_called_once()
