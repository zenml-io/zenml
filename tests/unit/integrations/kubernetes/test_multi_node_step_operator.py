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
"""Unit tests for multi-node command steps on the K8s step operator."""

import pytest
from kubernetes import client as k8s_client

from zenml.integrations.kubernetes.step_operators.kubernetes_step_operator import (
    MULTI_NODE_RENDEZVOUS_PORT,
    apply_indexed_completion,
    build_headless_service_manifest,
    build_rank_dispatch_command,
    multi_node_environment,
    validate_multi_node_step,
)


def _job(name: str = "job-x") -> k8s_client.V1Job:
    """Build a minimal job manifest.

    Args:
        name: The job name.

    Returns:
        The job manifest.
    """
    return k8s_client.V1Job(
        metadata=k8s_client.V1ObjectMeta(
            name=name, uid="uid-1", labels={"step_name": "train"}
        ),
        spec=k8s_client.V1JobSpec(
            parallelism=1,
            template=k8s_client.V1PodTemplateSpec(
                spec=k8s_client.V1PodSpec(containers=[])
            ),
        ),
    )


class TestValidation:
    def test_regular_step_multi_node_refused(self) -> None:
        with pytest.raises(RuntimeError, match="regular step"):
            validate_multi_node_step(
                node_count=2, is_command_step=False, step_name="train"
            )

    def test_command_step_multi_node_allowed(self) -> None:
        validate_multi_node_step(
            node_count=4, is_command_step=True, step_name="train"
        )

    def test_single_node_regular_step_allowed(self) -> None:
        validate_multi_node_step(
            node_count=1, is_command_step=False, step_name="train"
        )


class TestManifests:
    def test_indexed_completion(self) -> None:
        job = _job()
        apply_indexed_completion(job, node_count=3)
        assert job.spec.parallelism == 3
        assert job.spec.completions == 3
        assert job.spec.completion_mode == "Indexed"
        # Pod hostname + service subdomain give stable per-pod DNS.
        assert job.spec.template.spec.subdomain == "job-x"

    def test_rendezvous_environment(self) -> None:
        env = multi_node_environment(
            job_name="job-x", namespace="zenml", node_count=3
        )
        assert env["ZENML_NODE_COUNT"] == "3"
        assert env["ZENML_MASTER_ADDR"] == "job-x-0.job-x.zenml.svc"
        assert env["ZENML_MASTER_PORT"] == str(MULTI_NODE_RENDEZVOUS_PORT)

    def test_rank_dispatch_command(self) -> None:
        """Rank 0 runs the ZenML entrypoint; other ranks the raw command.

        N concurrent ZenML step entrypoints for one step_run_id would
        race on status, logs, and the success publish — exactly one pod
        may do the bookkeeping.
        """
        dispatch = build_rank_dispatch_command(
            zenml_entrypoint_command=["python", "-m", "zenml.entrypoint"],
            raw_command=["bash", "-lc", "torchrun train.py"],
        )
        assert dispatch[:2] == ["/bin/sh", "-c"]
        script = dispatch[2]
        assert '"${JOB_COMPLETION_INDEX:-0}" = "0"' in script
        assert "exec python -m zenml.entrypoint" in script
        assert "exec bash -lc 'torchrun train.py'" in script

    def test_headless_service_owned_by_job(self) -> None:
        service = build_headless_service_manifest(_job())
        assert service.spec.cluster_ip == "None"
        assert service.spec.selector == {"job-name": "job-x"}
        assert service.spec.publish_not_ready_addresses is True
        owner = service.metadata.owner_references[0]
        assert owner.kind == "Job"
        assert owner.name == "job-x"
        assert owner.uid == "uid-1"
