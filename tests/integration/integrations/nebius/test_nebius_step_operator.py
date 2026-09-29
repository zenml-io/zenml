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
"""Local behavior tests; no Nebius credentials or cloud calls are used."""

import copy
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

pytest.importorskip("nebius")

from grpc import StatusCode
from nebius.aio.service_error import RequestError, RequestStatusExtended
from nebius.api.nebius.ai.v1 import Job, JobStatus
from nebius.api.nebius.common.v1 import ResourceMetadata

from zenml.config import ResourceSettings
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.nebius import job_client
from zenml.integrations.nebius.flavors import NebiusStepOperatorConfig
from zenml.integrations.nebius.remote_bootstrap import encode_argv
from zenml.integrations.nebius.step_operators import NebiusStepOperator
from zenml.integrations.nebius.step_operators import (
    nebius_step_operator as operator_module,
)
from zenml.integrations.nebius.submission import RECEIPT_KEY, SubmissionReceipt

IMAGE = "registry.example/step@sha256:" + "a" * 64


class Clock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def harness(monkeypatch):
    config = NebiusStepOperatorConfig(
        project_id="project-test",
        subnet_id="vpcsubnet-test",
        platform="gpu-l40s-a",
        preset="1gpu-8vcpu-32gb",
        total_timeout_seconds=10,
        provisioning_timeout_seconds=5,
        cancel_timeout_seconds=3,
        request_timeout_seconds=1,
        poll_interval_seconds=1,
        publication_grace_seconds=2,
    )
    operator = NebiusStepOperator(
        name="nebius-gpu",
        id=uuid4(),
        config=config,
        flavor="nebius",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    run = SimpleNamespace(
        id=uuid4(), run_metadata={}, status=ExecutionStatus.RUNNING, outputs={}
    )
    store = SimpleNamespace(
        metadata={}, local=False, fail_at=None, writes=0, offline=False
    )
    cloud = SimpleNamespace(
        job=None,
        creates=0,
        cancels=0,
        mode="ok",
        get_error=False,
        cancel_error=False,
        cancel_finishes=True,
    )
    clock = Clock()
    monkeypatch.setattr(operator_module, "time", clock)

    def fetch(*args, **kwargs):
        if store.offline:
            raise OSError("sensitive server detail")
        return SimpleNamespace(
            id=run.id,
            run_metadata=copy.deepcopy(store.metadata),
            status=run.status,
            outputs=run.outputs,
        )

    def publish(step_id, metadata):
        store.writes += 1
        if store.writes == store.fail_at or store.offline:
            raise OSError("secret-store-error")
        store.metadata.update(copy.deepcopy(metadata[operator.id]))

    monkeypatch.setattr(
        operator_module,
        "Client",
        lambda: SimpleNamespace(
            get_run_step=fetch,
            zen_store=SimpleNamespace(is_local_store=lambda: store.local),
        ),
    )
    monkeypatch.setattr(operator_module, "publish_step_run_metadata", publish)
    monkeypatch.setattr(operator, "get_settings", lambda info: config)

    class FakeClient:
        timeout = 1

        def create(self, request, key, acknowledged):
            cloud.creates += 1
            cloud.request = request
            cloud.key = key
            cloud.job = Job(
                metadata=ResourceMetadata(
                    id="aijob-test",
                    parent_id=config.project_id,
                    labels=request.metadata.labels,
                ),
                spec=request.spec,
                status=JobStatus(state=JobStatus.State.RUNNING),
            )
            if cloud.mode == "permission_denied":
                raise RequestError(
                    RequestStatusExtended(
                        code=StatusCode.PERMISSION_DENIED,
                        message="sensitive-server-message",
                        details=[],
                        service_errors=[],
                        request_id="11111111-2222-4333-8444-555555555555",
                        trace_id="sensitive-trace-value",
                    )
                )
            if cloud.mode == "lost_ack":
                raise OSError("secret-create-error")
            if cloud.mode == "operation_only":
                acknowledged("operation-test", "")
                raise TimeoutError("secret-operation-error")
            acknowledged("operation-test", "aijob-test")
            return "aijob-test"

        def get(self, job_id):
            if cloud.get_error:
                raise OSError("secret-get-error")
            return cloud.job

        def cancel(self, job_id, key):
            cloud.cancels += 1
            if cloud.cancel_finishes:
                cloud.job.status.state = JobStatus.State.CANCELLED
            if cloud.cancel_error:
                raise OSError("secret-cancel-error")

        def find_candidates(self, receipt):
            return [cloud.job.metadata.id] if cloud.job else []

    @contextmanager
    def connect(*args, **kwargs):
        yield FakeClient()

    monkeypatch.setattr(job_client, "connect", connect)
    info = SimpleNamespace(
        snapshot=SimpleNamespace(is_dynamic=False),
        config=SimpleNamespace(
            command=None,
            retry=None,
            resource_settings=ResourceSettings(),
            outputs={"result": None},
        ),
        step_run=run,
        step_run_id=run.id,
        run_id=uuid4(),
        get_image=lambda key: IMAGE,
    )
    return SimpleNamespace(
        operator=operator,
        config=config,
        run=run,
        store=store,
        cloud=cloud,
        clock=clock,
        info=info,
    )


def submit(h):
    h.operator.submit(
        h.info,
        ["python", "-m", "zenml.entrypoints.step_entrypoint"],
        {"ZENML_STORE_API_TOKEN": "private-token"},
    )


def receipt(h):
    return SubmissionReceipt.model_validate_json(
        h.run.run_metadata[RECEIPT_KEY]
    )


def test_submit_persists_ids_and_runtime_secrets_are_not_in_receipt(harness):
    h = harness
    submit(h)
    saved = receipt(h)
    assert saved.job_id == "aijob-test"
    assert saved.operation_id == "operation-test"
    assert h.cloud.key == saved.submission_id
    assert h.cloud.request.spec.restart_attempts == 0
    assert not h.cloud.request.spec.preemptible
    assert (
        h.cloud.request.spec.environment_variables[0].value == "private-token"
    )
    assert "private-token" not in saved.model_dump_json()
    assert (
        "private-token"
        not in h.cloud.request.spec.injected_files[0].content.decode()
    )
    assert h.store.writes == 2


def test_duplicate_submit_does_not_create_a_second_job(harness):
    h = harness
    submit(h)
    with pytest.raises(RuntimeError, match="already has"):
        submit(h)
    assert h.cloud.creates == 1


def test_receipt_failure_prevents_create(harness):
    h = harness
    h.store.fail_at = 1
    with pytest.raises(OSError):
        submit(h)
    assert h.cloud.creates == 0


@pytest.mark.parametrize(
    "mode,operation",
    [("lost_ack", None), ("operation_only", "operation-test")],
)
def test_ambiguous_create_retains_receipt_without_retry_or_cancel(
    harness, mode, operation
):
    h = harness
    h.cloud.mode = mode
    with pytest.raises(RuntimeError, match="Do not resubmit") as error:
        submit(h)
    assert "secret-" not in str(error.value)
    assert h.cloud.creates == 1 and h.cloud.cancels == 0
    assert receipt(h).operation_id == operation and receipt(h).job_id is None
    assert h.operator.find_submission_jobs(h.run) == ["aijob-test"]
    with pytest.raises(RuntimeError):
        submit(h)
    assert h.cloud.creates == 1


def test_metadata_failure_after_ack_cancels_known_id(harness):
    h = harness
    h.store.fail_at = 2
    with pytest.raises(RuntimeError) as error:
        submit(h)
    assert "secret-store-error" not in str(error.value)
    assert receipt(h).job_id == "aijob-test"
    assert h.cloud.cancels == 1
    assert receipt(h).cleanup == "WORKLOAD_TERMINAL"


@pytest.mark.parametrize(
    "state,expected",
    [
        ("PROVISIONING", ExecutionStatus.PROVISIONING),
        ("IMAGE_PULLING", ExecutionStatus.PROVISIONING),
        ("STARTING", ExecutionStatus.PROVISIONING),
        ("RUNNING", ExecutionStatus.RUNNING),
        ("CANCELLING", ExecutionStatus.CANCELLING),
        ("CANCELLED", ExecutionStatus.CANCELLED),
        ("FAILED", ExecutionStatus.FAILED),
        ("ERROR", ExecutionStatus.FAILED),
        ("DELETING", ExecutionStatus.PROVISIONING),
        ("STATE_UNSPECIFIED", ExecutionStatus.PROVISIONING),
    ],
)
def test_provider_state_mapping(harness, state, expected):
    h = harness
    submit(h)
    h.cloud.job.status.state = JobStatus.State[state]
    assert h.operator.get_status(h.run) == expected


def test_cloud_success_requires_published_step_and_expected_artifacts(harness):
    h = harness
    submit(h)
    h.cloud.job.status.state = JobStatus.State.COMPLETED
    assert h.operator.get_status(h.run) == ExecutionStatus.RUNNING
    h.run.status = ExecutionStatus.COMPLETED
    assert h.operator.get_status(h.run) == ExecutionStatus.RUNNING
    h.run.outputs = {"result": [object()]}
    assert h.operator.get_status(h.run) == ExecutionStatus.COMPLETED


def test_exit_zero_without_zenml_publication_fails_after_grace(harness):
    h = harness
    submit(h)
    h.cloud.job.status.state = JobStatus.State.COMPLETED
    assert h.operator.wait(h.run) == ExecutionStatus.FAILED
    assert h.clock.now == 1002


def test_zenml_success_does_not_end_active_cloud_supervision(harness):
    h = harness
    submit(h)
    h.run.status = ExecutionStatus.COMPLETED
    h.run.outputs = {"result": [object()]}
    with pytest.raises(TimeoutError):
        h.operator.wait(h.run)
    assert h.cloud.cancels == 1


def test_read_failure_is_bounded_and_redacted(harness):
    h = harness
    submit(h)
    h.cloud.get_error = True
    with pytest.raises(TimeoutError) as error:
        h.operator.wait(h.run)
    assert "secret-get-error" not in str(error.value)
    assert h.cloud.cancels == 1
    assert receipt(h).cleanup == "UNCONFIRMED"
    assert h.clock.now <= 1013


def test_provisioning_deadline_cancels(harness):
    h = harness
    submit(h)
    h.cloud.job.status.state = JobStatus.State.PROVISIONING
    with pytest.raises(TimeoutError, match="provisioning"):
        h.operator.wait(h.run)
    assert h.cloud.cancels == 1
    assert h.clock.now == 1005


def test_cancel_completion_race_preserves_success(harness):
    h = harness
    submit(h)
    h.cloud.job.status.state = JobStatus.State.COMPLETED
    h.operator.cancel(h.run)
    assert h.cloud.cancels == 0
    assert receipt(h).provider_state == "COMPLETED"


def test_cancel_lost_ack_is_confirmed_by_read_without_replay(harness):
    h = harness
    submit(h)
    h.cloud.cancel_error = True
    h.operator.cancel(h.run)
    h.operator.cancel(h.run)
    h.operator.cleanup_step_submission(h.run)
    assert h.cloud.cancels == 1
    assert receipt(h).cleanup == "WORKLOAD_TERMINAL"


def test_unconfirmed_cancel_is_not_repeated_by_cleanup(harness):
    h = harness
    submit(h)
    h.cloud.cancel_finishes = False
    h.cloud.cancel_error = True
    with pytest.raises(RuntimeError, match="unconfirmed"):
        h.operator.cancel(h.run)
    h.operator.cleanup_step_submission(h.run)
    assert h.cloud.cancels == 1
    assert receipt(h).cleanup == "UNCONFIRMED"


def test_keyboard_interrupt_cancels_and_preserves_original(
    harness, monkeypatch
):
    h = harness
    submit(h)
    monkeypatch.setattr(
        h.operator, "get_status", Mock(side_effect=KeyboardInterrupt)
    )
    with pytest.raises(KeyboardInterrupt):
        h.operator.wait(h.run)
    assert h.cloud.cancels == 1


def test_store_outage_retains_newer_local_acknowledgement(harness):
    h = harness
    submit(h)
    h.store.metadata[RECEIPT_KEY] = (
        receipt(h)
        .model_copy(update={"revision": 1, "job_id": None})
        .model_dump_json()
    )
    h.operator.cancel(h.run)
    assert h.cloud.cancels == 1


@pytest.mark.parametrize(
    "kind",
    [
        "dynamic",
        "command",
        "retry",
        "cpu",
        "multi_gpu",
        "gpu_class",
        "pool",
        "local_store",
        "mutable_image",
    ],
)
def test_unsupported_steps_fail_before_create(harness, kind):
    h = harness
    if kind == "dynamic":
        h.info.snapshot.is_dynamic = True
    elif kind == "command":
        h.info.config.command = "echo hi"
    elif kind == "retry":
        h.info.config.retry = object()
    elif kind == "cpu":
        h.info.config.resource_settings = ResourceSettings(cpu_count=2)
    elif kind == "multi_gpu":
        h.info.config.resource_settings = ResourceSettings(gpu_count=2)
    elif kind == "gpu_class":
        h.info.config.resource_settings = ResourceSettings(gpu_class="H100")
    elif kind == "pool":
        h.info.config.resource_settings = ResourceSettings(resources="gpu")
    elif kind == "local_store":
        h.store.local = True
    else:
        h.info.get_image = lambda key: "registry/image:latest"
    with pytest.raises(ValueError):
        submit(h)
    assert h.cloud.creates == 0


def test_generic_single_gpu_is_accepted(harness):
    harness.info.config.resource_settings = ResourceSettings(gpu_count=1)
    submit(harness)
    assert harness.cloud.creates == 1


def test_flavor_does_not_import_optional_sdk():
    script = """
import sys
class Block:
    def find_spec(self, fullname, *args):
        if fullname == "nebius" or fullname.startswith("nebius."):
            raise RuntimeError("optional SDK imported")
sys.meta_path.insert(0, Block())
from zenml.integrations.nebius import NebiusIntegration
flavor = NebiusIntegration.flavors()[0]()
assert flavor.name == "nebius"
assert flavor.config_class(project_id="p", subnet_id="s").is_remote
"""
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        env=os.environ.copy(),
        capture_output=True,
    )


def test_bootstrap_preserves_argv_environment_and_exit_code(tmp_path):
    output = tmp_path / "argv.json"
    command = [
        sys.executable,
        "-c",
        "import json,sys,os;json.dump([sys.argv[1:],os.environ['PROBE']],open(sys.argv[1],'w'));sys.exit(7)",
        str(output),
        "a b",
        "'quoted'",
        "$(touch not-created)",
        "λ",
    ]
    payload = tmp_path / "command.json"
    payload.write_bytes(encode_argv(command))
    env = {**os.environ, "PROBE": "runtime-value"}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "zenml.integrations.nebius.remote_bootstrap",
            str(payload),
        ],
        env=env,
    )
    assert result.returncode == 7
    assert json.loads(output.read_text()) == [command[3:], "runtime-value"]
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize(
    "argv",
    [[], [""], ["python", "bad\0arg"], ["python", "x" * 65536], ["python", 1]],
)
def test_bad_argv_fails_locally(argv):
    with pytest.raises(ValueError):
        encode_argv(argv)


def test_native_secrets_do_not_override_runtime(harness):
    h = harness
    settings = h.config.model_copy(
        update={
            "environment_secret_versions": {
                "ZENML_STORE_API_TOKEN": "mbsecver-test"
            }
        }
    )
    with pytest.raises(ValueError, match="override"):
        job_client.build_spec(
            h.config,
            settings,
            IMAGE,
            ["python"],
            {"ZENML_STORE_API_TOKEN": "private"},
        )


def test_request_round_trip_and_fingerprint_excludes_secret_values(harness):
    h = harness
    a = job_client.build_spec(
        h.config, h.config, IMAGE, ["python"], {"TOKEN": "secret-a"}
    )
    b = job_client.build_spec(
        h.config, h.config, IMAGE, ["python"], {"TOKEN": "secret-b"}
    )
    assert job_client.spec_fingerprint(a) == job_client.spec_fingerprint(b)
    restored = type(a)()
    restored.ParseFromString(a.SerializeToString())
    assert restored.environment_variables[0].value == "secret-a"
    assert restored.injected_files[0].content == encode_argv(["python"])
    assert restored.disk.size_bytes == 100 * 1024**3


@pytest.mark.parametrize(
    "setting", ["preemptible", "restart_attempts", "unknown"]
)
def test_unknown_settings_are_rejected(setting):
    with pytest.raises(ValueError, match="Unsupported Nebius settings"):
        NebiusStepOperatorConfig(
            project_id="p", subnet_id="s", **{setting: True}
        )


def test_terminal_job_is_not_cancelled_when_metadata_is_offline(harness):
    h = harness
    submit(h)
    h.cloud.job.status.state = JobStatus.State.COMPLETED
    h.store.offline = True
    h.operator.cancel(h.run)
    assert h.cloud.cancels == 0
    saved = SubmissionReceipt.model_validate_json(
        h.run.run_metadata[RECEIPT_KEY]
    )
    assert saved.cleanup == "WORKLOAD_TERMINAL"


def test_permission_denied_retains_safe_diagnostics_without_replaying(harness):
    harness.cloud.mode = "permission_denied"
    with pytest.raises(RuntimeError, match="PERMISSION_DENIED") as error:
        submit(harness)
    saved = receipt(harness)
    assert saved.submission_error_code == "PERMISSION_DENIED"
    assert (
        saved.submission_request_id == "11111111-2222-4333-8444-555555555555"
    )
    assert saved.job_id is None
    assert "sensitive" not in str(error.value)
    with pytest.raises(RuntimeError, match="already has"):
        submit(harness)
    assert harness.cloud.creates == 1


@pytest.mark.parametrize("length", [127, 128, 129, 143])
def test_image_reference_length_boundary_before_submission(harness, length):
    h = harness
    suffix = "@sha256:" + "a" * 64
    prefix = "registry.example/"
    image = prefix + "x" * (length - len(prefix) - len(suffix)) + suffix
    h.info.get_image = lambda key: image
    if length <= 128:
        submit(h)
        assert h.cloud.request.spec.image == image
        assert h.cloud.creates == 1
    else:
        with pytest.raises(ValueError, match="default_repository"):
            submit(h)
        assert h.cloud.creates == 0
        assert h.store.writes == 0
        assert RECEIPT_KEY not in h.run.run_metadata
