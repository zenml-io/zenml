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
"""Unit tests for the Slurm orchestrator.

The Slurm CLI and SSH are never invoked: the orchestrator is driven through an
in-memory fake command runner, so the tests run without a cluster.
"""

from datetime import datetime
from types import SimpleNamespace
from typing import Dict, List, Optional
from uuid import uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.constants import METADATA_ORCHESTRATOR_RUN_ID
from zenml.enums import ExecutionMode, ExecutionStatus, StackComponentType
from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner
from zenml.integrations.slurm.flavors import (
    SlurmOrchestratorConfig,
    SlurmOrchestratorFlavor,
    SlurmOrchestratorSettings,
)
from zenml.integrations.slurm.orchestrators import SlurmOrchestrator
from zenml.integrations.slurm.orchestrators.slurm_orchestrator import (
    ENV_ZENML_SLURM_RUN_ID,
    SLURM_CLEANUP_JOB_ID_METADATA_KEY,
    SLURM_ISOLATED_JOB_ID_METADATA_KEY,
    SLURM_ISOLATED_JOB_IDS_METADATA_KEY,
    SLURM_JOB_IDS_METADATA_KEY,
    SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY,
)
from zenml.integrations.slurm.slurm_client import (
    CommandResult,
    SlurmClient,
    SlurmCommandRunner,
)

SECRET_TOKEN = "super-secret-zenml-token"
IMAGE = "registry.example.com/zenml:abc123"


class FakeRunner(SlurmCommandRunner):
    """In-memory fake host that hands out incrementing job ids."""

    def __init__(self) -> None:
        """Initialize the fake."""
        self.files: Dict[str, str] = {}
        self.modes: Dict[str, int] = {}
        self.commands: List[str] = []
        self._next_job_id = 1000

    def run(self, command: str) -> CommandResult:
        """Record the command; return a fresh job id for each sbatch.

        Args:
            command: The command line.

        Returns:
            The command result.
        """
        self.commands.append(command)
        if command.startswith("sbatch"):
            job_id = str(self._next_job_id)
            self._next_job_id += 1
            return CommandResult(exit_code=0, stdout=job_id, stderr="")
        return CommandResult(exit_code=0, stdout="", stderr="")

    def put_text(
        self, remote_path: str, content: str, mode: int = 0o600
    ) -> None:
        """Record a written file and its mode.

        Args:
            remote_path: Destination path.
            content: The content written.
            mode: The file mode.
        """
        self.files[remote_path] = content
        self.modes[remote_path] = mode

    def read_text(self, remote_path: str) -> str:
        """Read a recorded file.

        Args:
            remote_path: Path to read.

        Returns:
            The recorded content.

        Raises:
            FileNotFoundError: If nothing was recorded at that path.
        """
        if remote_path not in self.files:
            raise FileNotFoundError(remote_path)
        return self.files[remote_path]


def _build_orchestrator(
    config: Optional[SlurmOrchestratorConfig] = None,
) -> SlurmOrchestrator:
    """Construct a Slurm orchestrator.

    Args:
        config: The config for the orchestrator.

    Returns:
        A SlurmOrchestrator instance.
    """
    return SlurmOrchestrator(
        name="",
        id=uuid4(),
        config=config
        or SlurmOrchestratorConfig(transport="local", workdir="/runs"),
        flavor="slurm",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _step(upstream: List[str], gpu: int = 0) -> SimpleNamespace:
    """Build a Step stand-in.

    Args:
        upstream: Invocation ids this step depends on.
        gpu: Number of GPUs the step requests.

    Returns:
        A namespace usable where a Step is expected.
    """
    return SimpleNamespace(
        spec=SimpleNamespace(upstream_steps=upstream),
        config=SimpleNamespace(
            resource_settings=ResourceSettings(gpu_count=gpu or None)
        ),
    )


def _snapshot(steps: Dict[str, SimpleNamespace]) -> SimpleNamespace:
    """Build a PipelineSnapshotResponse stand-in.

    Args:
        steps: The step configurations keyed by invocation id.

    Returns:
        A namespace usable where a snapshot is expected.
    """
    return SimpleNamespace(
        id=uuid4(),
        build=SimpleNamespace(
            get_image=lambda component_key, step: IMAGE,
        ),
        step_configurations=steps,
        pipeline_configuration=SimpleNamespace(name="p"),
        schedule=None,
        stack=SimpleNamespace(id=uuid4()),
    )


# --- flavor / config ----------------------------------------------------------


def test_flavor_identity():
    """The flavor identifier and classes are Slurm's."""
    flavor = SlurmOrchestratorFlavor()
    assert flavor.name == "slurm"
    assert flavor.config_class is SlurmOrchestratorConfig
    assert flavor.implementation_class is SlurmOrchestrator


def test_ssh_transport_requires_connection_details():
    """The ssh transport needs hostname and username; local does not."""
    with pytest.raises(ValueError):
        SlurmOrchestratorConfig(transport="ssh", workdir="/s")

    SlurmOrchestratorConfig(transport="local", workdir="/s")
    SlurmOrchestratorConfig(
        transport="ssh", workdir="/s", hostname="h", username="u"
    )


def test_orchestrator_is_remote_and_detached():
    """The orchestrator runs remotely and does not wait for completion."""
    config = SlurmOrchestratorConfig(transport="local", workdir="/s")
    assert config.is_remote is True
    assert config.is_synchronous is False


def test_orchestrator_supports_failure_modes():
    """The orchestrator advertises the failure modes it implements."""
    op = _build_orchestrator()
    assert op.supported_execution_modes == [
        ExecutionMode.FAIL_FAST,
        ExecutionMode.STOP_ON_FAILURE,
        ExecutionMode.CONTINUE_ON_FAILURE,
    ]


# --- run id -------------------------------------------------------------------


def test_get_orchestrator_run_id_reads_env(monkeypatch):
    """The run id comes from the injected environment variable."""
    op = _build_orchestrator()
    monkeypatch.setenv(ENV_ZENML_SLURM_RUN_ID, "the-run-id")
    assert op.get_orchestrator_run_id() == "the-run-id"


def test_get_orchestrator_run_id_raises_when_unset(monkeypatch):
    """Without the env var, the run id lookup fails loudly."""
    op = _build_orchestrator()
    monkeypatch.delenv(ENV_ZENML_SLURM_RUN_ID, raising=False)
    with pytest.raises(RuntimeError):
        op.get_orchestrator_run_id()


# --- topological ordering -----------------------------------------------------


def test_sorted_steps_is_topological():
    """Upstream steps are submitted before their dependents."""
    # Declared out of order: a dependent appears before its parent.
    steps = {
        "evaluate": _step(["train"]),
        "train": _step(["load"]),
        "load": _step([]),
    }
    order = SlurmOrchestrator._sorted_step_names(steps)
    assert order.index("load") < order.index("train")
    assert order.index("train") < order.index("evaluate")


# --- submit -------------------------------------------------------------------


def _use_fake_client(monkeypatch, runner: FakeRunner) -> None:
    """Route the orchestrator's client factory to the fake runner.

    Args:
        monkeypatch: The pytest monkeypatch fixture.
        runner: The fake runner to hand back.
    """
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".build_slurm_client",
        lambda config: SlurmClient(runner),
    )


def _placeholder_run() -> SimpleNamespace:
    """Build a PipelineRunResponse stand-in with a unique id.

    Returns:
        A namespace usable where a placeholder run is expected.
    """
    return SimpleNamespace(id=uuid4())


def _stack(
    credentials: Optional["tuple[str, str]"] = None,
) -> SimpleNamespace:
    """Build a stack stand-in with a remote container registry.

    Args:
        credentials: Optional registry username and password.

    Returns:
        A namespace usable where a stack is expected.
    """
    return SimpleNamespace(
        container_registry=SimpleNamespace(
            config=SimpleNamespace(uri="registry.example.com"),
            credentials=credentials,
        )
    )


def _isolated_step_info(
    snapshot: Optional[SimpleNamespace] = None,
) -> SimpleNamespace:
    """Build a dynamic isolated StepRunInfo stand-in.

    Args:
        snapshot: Optional snapshot to attach to the step run info.

    Returns:
        A namespace usable where StepRunInfo is expected.
    """
    return SimpleNamespace(
        step_run_id=uuid4(),
        run_id=uuid4(),
        pipeline_step_name="dynamic_train",
        config=SimpleNamespace(resource_settings=ResourceSettings(cpu_count=2)),
        snapshot=snapshot or _snapshot({}),
        step_run=SimpleNamespace(run_metadata={}),
        get_image=lambda key: IMAGE,
    )


def _run(
    run_id,
    run_metadata: Dict[str, object],
    execution_mode: ExecutionMode = ExecutionMode.CONTINUE_ON_FAILURE,
) -> SimpleNamespace:
    """Build a PipelineRunResponse stand-in.

    Args:
        run_id: The run ID.
        run_metadata: Run metadata to attach.
        execution_mode: Pipeline execution mode.

    Returns:
        A namespace usable where a PipelineRunResponse is expected.
    """
    return SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.PROVISIONING,
        config=SimpleNamespace(execution_mode=execution_mode),
        run_metadata=run_metadata,
    )


def _submit_two_step_dag(monkeypatch) -> "tuple[FakeRunner, str]":
    """Submit a load -> train DAG and return the fake host and run id.

    Args:
        monkeypatch: The pytest monkeypatch fixture.

    Returns:
        The fake runner recording everything the submission did, and the
        orchestrator run id (the placeholder run id).
    """
    op = _build_orchestrator()
    op.get_settings = lambda _step: SlurmOrchestratorSettings()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)

    snapshot = _snapshot({"load": _step([]), "train": _step(["load"], gpu=1)})
    placeholder = _placeholder_run()
    op.submit_pipeline(
        snapshot=snapshot,
        stack=_stack(),
        base_environment={},
        step_environments={
            "load": {"ZENML_STORE_API_KEY": SECRET_TOKEN},
            "train": {"ZENML_STORE_API_KEY": SECRET_TOKEN},
        },
        placeholder_run=placeholder,
    )
    return runner, str(placeholder.id)


def test_submit_returns_slurm_metadata(monkeypatch):
    """Submitted job ids and the run id are attached to the run metadata."""
    op = _build_orchestrator()
    op.get_settings = lambda _step: SlurmOrchestratorSettings()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    snapshot = _snapshot({"load": _step([]), "train": _step(["load"])})
    placeholder = _placeholder_run()

    result = op.submit_pipeline(
        snapshot=snapshot,
        stack=_stack(),
        base_environment={},
        step_environments={"load": {}, "train": {}},
        placeholder_run=placeholder,
    )

    assert result is not None
    assert result.metadata == {
        METADATA_ORCHESTRATOR_RUN_ID: str(placeholder.id),
        SLURM_JOB_IDS_METADATA_KEY: {"load": "1000", "train": "1001"},
        SLURM_CLEANUP_JOB_ID_METADATA_KEY: "1002",
    }


def test_submit_wires_dependencies_in_topological_order(monkeypatch):
    """The dependent step's job waits on the parent's job id."""
    runner, _ = _submit_two_step_dag(monkeypatch)
    sbatch = [c for c in runner.commands if c.startswith("sbatch")]
    assert len(sbatch) == 3
    # load submitted first (job id 1000, no dependency), train second.
    assert "--dependency" not in sbatch[0]
    assert "--dependency=afterok:1000" in sbatch[1]
    assert "--kill-on-invalid-dep=yes" in sbatch[1]
    assert "--dependency=afterany:1000:1001" in sbatch[2]
    cleanup_scripts = [
        content
        for path, content in runner.files.items()
        if path.endswith("/cleanup/job.sh")
    ]
    assert len(cleanup_scripts) == 1
    assert "/env" in cleanup_scripts[0]
    assert "cleanup_complete" in cleanup_scripts[0]


def test_cleanup_job_inherits_extra_sbatch_directives(monkeypatch):
    """Cleanup jobs preserve cluster-specific sbatch directives."""
    op = _build_orchestrator()

    def _settings(obj):
        if hasattr(obj, "pipeline_configuration"):
            return SlurmOrchestratorSettings(
                extra_sbatch_directives=["--constraint=a100"]
            )
        return SlurmOrchestratorSettings()

    op.get_settings = _settings
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    op.submit_pipeline(
        snapshot=_snapshot({"load": _step([])}),
        stack=_stack(),
        base_environment={},
        step_environments={"load": {}},
        placeholder_run=_placeholder_run(),
    )

    cleanup_script = next(
        content
        for path, content in runner.files.items()
        if path.endswith("/cleanup/job.sh")
    )
    assert "#SBATCH --constraint=a100" in cleanup_script


def test_submit_injects_placeholder_run_id_into_step_env(monkeypatch):
    """Each step's env file carries the placeholder run id as the run id."""
    runner, run_id = _submit_two_step_dag(monkeypatch)
    env_files = [c for p, c in runner.files.items() if p.endswith("/env")]
    assert env_files
    # The run id is the placeholder run id (unique per run), not the snapshot
    # id (which repeats across runs of the same snapshot).
    assert all(
        f"{ENV_ZENML_SLURM_RUN_ID}={run_id}" in content
        for content in env_files
    )


def test_submit_uses_placeholder_run_id_for_paths(monkeypatch):
    """Staging paths are namespaced by the placeholder run id."""
    runner, run_id = _submit_two_step_dag(monkeypatch)
    assert all(f"/{run_id}/" in path for path in runner.files)


def test_submit_requires_a_placeholder_run(monkeypatch):
    """Submission without a placeholder run is rejected (no run id)."""
    op = _build_orchestrator()
    op.get_settings = lambda _step: SlurmOrchestratorSettings()
    _use_fake_client(monkeypatch, FakeRunner())
    with pytest.raises(AssertionError):
        op.submit_pipeline(
            snapshot=_snapshot({"load": _step([])}),
            stack=_stack(),
            base_environment={},
            step_environments={"load": {}},
            placeholder_run=None,
        )


def test_submit_rejects_scheduled_pipelines(monkeypatch):
    """The orchestrator refuses scheduled pipelines with a clear error."""
    op = _build_orchestrator()
    _use_fake_client(monkeypatch, FakeRunner())
    snapshot = _snapshot({"load": _step([])})
    snapshot.schedule = SimpleNamespace(name="daily")
    with pytest.raises(RuntimeError, match="does not support scheduled"):
        op.submit_pipeline(
            snapshot=snapshot,
            stack=_stack(),
            base_environment={},
            step_environments={"load": {}},
            placeholder_run=_placeholder_run(),
        )


def test_submit_dynamic_pipeline_submits_orchestration_job(monkeypatch):
    """Dynamic pipelines launch a Slurm orchestration job."""
    op = _build_orchestrator()
    op.get_settings = lambda _snapshot: SlurmOrchestratorSettings()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    placeholder = _placeholder_run()

    result = op.submit_dynamic_pipeline(
        snapshot=_snapshot({}),
        stack=_stack(),
        environment={"ZENML_STORE_API_KEY": SECRET_TOKEN},
        placeholder_run=placeholder,
    )

    assert result is not None
    assert result.metadata == {
        METADATA_ORCHESTRATOR_RUN_ID: str(placeholder.id),
        SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY: "1000",
    }
    sbatch = [c for c in runner.commands if c.startswith("sbatch")]
    assert len(sbatch) == 1
    assert "orchestration/job.sh" in sbatch[0]
    env_file = runner.files[f"/runs/{placeholder.id}/orchestration/env"]
    assert f"{ENV_ZENML_SLURM_RUN_ID}={placeholder.id}" in env_file
    assert SECRET_TOKEN in env_file


def test_submit_dynamic_pipeline_rejects_schedules(monkeypatch):
    """Scheduled dynamic pipelines are rejected consistently."""
    op = _build_orchestrator()
    _use_fake_client(monkeypatch, FakeRunner())
    snapshot = _snapshot({})
    snapshot.schedule = SimpleNamespace(name="daily")

    with pytest.raises(RuntimeError, match="does not support scheduled"):
        op.submit_dynamic_pipeline(
            snapshot=snapshot,
            stack=_stack(),
            environment={},
            placeholder_run=_placeholder_run(),
        )


def test_submit_keeps_secrets_off_the_command_line(monkeypatch):
    """Secrets live only in the 0600 env file, never on a command line."""
    runner, _ = _submit_two_step_dag(monkeypatch)
    assert all(SECRET_TOKEN not in c for c in runner.commands)

    env_files = {p: c for p, c in runner.files.items() if p.endswith("/env")}
    assert env_files
    for path, content in env_files.items():
        assert SECRET_TOKEN in content
        assert runner.modes[path] == 0o600
    scripts = {p: m for p, m in runner.modes.items() if p.endswith("job.sh")}
    assert scripts
    assert all(mode == 0o700 for mode in scripts.values())


def test_submit_cancels_queued_jobs_on_failure(monkeypatch):
    """A mid-DAG failure cancels the jobs already queued for the run."""
    op = _build_orchestrator()
    op.get_settings = lambda _step: SlurmOrchestratorSettings()

    class FailingRunner(FakeRunner):
        def put_text(self, remote_path, content, mode=0o600):
            # Fail while staging the second step, after the first is queued.
            if remote_path.endswith("/env") and self._next_job_id > 1000:
                raise RuntimeError("disk full")
            super().put_text(remote_path, content, mode=mode)

    runner = FailingRunner()
    _use_fake_client(monkeypatch, runner)
    snapshot = _snapshot({"load": _step([]), "train": _step(["load"])})
    with pytest.raises(RuntimeError):
        op.submit_pipeline(
            snapshot=snapshot,
            stack=_stack(),
            base_environment={},
            step_environments={"load": {}, "train": {}},
            placeholder_run=_placeholder_run(),
        )
    assert any(c.startswith("scancel 1000") for c in runner.commands)
    assert any(c.startswith("rm -rf -- ") for c in runner.commands)


def test_fetch_status_reports_pre_entrypoint_failure(monkeypatch):
    """A failed Slurm wrapper reconciles a detached run as failed."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    run_dir = op._run_dir(str(run_id), "load")
    runner.files[f"{run_dir}/exit_code"] = "1\n"
    run = _run(
        run_id=run_id,
        run_metadata={SLURM_JOB_IDS_METADATA_KEY: {"load": "1000"}},
    )

    pipeline_status, step_statuses = op.fetch_status(run, include_steps=True)

    assert pipeline_status is ExecutionStatus.FAILED
    assert step_statuses == {"load": ExecutionStatus.FAILED}


def test_fetch_status_uses_cleanup_marker_for_never_started_job(monkeypatch):
    """A dependency-cancelled job is terminal after cleanup completes."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    cleanup_marker = f"/runs/{run_id}/cleanup/cleanup_complete"
    runner.files[cleanup_marker] = ""
    run = _run(
        run_id=run_id,
        run_metadata={SLURM_JOB_IDS_METADATA_KEY: {"train": "1001"}},
    )

    pipeline_status, _ = op.fetch_status(run)

    assert pipeline_status is ExecutionStatus.FAILED


def test_fetch_status_continue_on_failure_keeps_siblings(monkeypatch):
    """Continue-on-failure does not cancel independent sibling jobs."""
    op = _build_orchestrator()

    class StatusRunner(FakeRunner):
        def run(self, command: str) -> CommandResult:
            self.commands.append(command)
            if command.startswith("squeue"):
                return CommandResult(
                    exit_code=0,
                    stdout=(
                        "1000|FAILED\n"
                        "1001|RUNNING\n"
                        "1002|PENDING\n"
                    ),
                    stderr="",
                )
            return CommandResult(exit_code=0, stdout="", stderr="")

    runner = StatusRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    run = _run(
        run_id=run_id,
        run_metadata={
            SLURM_JOB_IDS_METADATA_KEY: {
                "load": "1000",
                "train": "1001",
                "evaluate": "1002",
            }
        },
    )

    pipeline_status, step_statuses = op.fetch_status(run, include_steps=True)

    assert pipeline_status is ExecutionStatus.RUNNING
    assert step_statuses == {
        "load": ExecutionStatus.FAILED,
        "train": ExecutionStatus.RUNNING,
        "evaluate": ExecutionStatus.QUEUED,
    }
    assert [
        command for command in runner.commands if command.startswith("squeue")
    ] == ["squeue --noheader --format='%i|%T' --jobs=1000,1001,1002"]
    assert not any(
        command.startswith("scancel") for command in runner.commands
    )


def test_fetch_status_stop_on_failure_cancels_siblings(monkeypatch):
    """Stop-on-failure cancels unfinished sibling jobs."""
    op = _build_orchestrator()

    class StatusRunner(FakeRunner):
        def run(self, command: str) -> CommandResult:
            self.commands.append(command)
            if command.startswith("squeue"):
                return CommandResult(
                    exit_code=0,
                    stdout=(
                        "1000|FAILED\n"
                        "1001|RUNNING\n"
                        "1002|PENDING\n"
                    ),
                    stderr="",
                )
            return CommandResult(exit_code=0, stdout="", stderr="")

    runner = StatusRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    run = _run(
        run_id=run_id,
        run_metadata={
            SLURM_JOB_IDS_METADATA_KEY: {
                "load": "1000",
                "train": "1001",
                "evaluate": "1002",
            }
        },
        execution_mode=ExecutionMode.STOP_ON_FAILURE,
    )

    pipeline_status, _ = op.fetch_status(run)

    assert pipeline_status is ExecutionStatus.FAILED
    assert any(
        command == "scancel 1001 1002" for command in runner.commands
    )
    assert (
        runner.files[f"{op._run_dir(str(run_id), 'train')}/cancelled"]
        == "1\n"
    )
    assert (
        runner.files[f"{op._run_dir(str(run_id), 'evaluate')}/cancelled"]
        == "1\n"
    )
    assert any(
        command.startswith("rm -rf --")
        and f"{op._run_dir(str(run_id), 'train')}/env" in command
        for command in runner.commands
    )


def test_stop_run_cancels_submitted_jobs(monkeypatch):
    """Stopping a detached Slurm run scancels all submitted step jobs."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    monkeypatch.setattr(
        "zenml.orchestrators.base_orchestrator"
        ".publish_pipeline_run_status_update",
        lambda **kwargs: None,
    )
    run_id = uuid4()
    run = SimpleNamespace(
        id=run_id,
        orchestrator_run_id=str(run_id),
        run_metadata={
            SLURM_JOB_IDS_METADATA_KEY: {"load": "1000", "train": "1001"}
        },
    )

    op.stop_run(run)

    assert any(
        command == "scancel 1000 1001" for command in runner.commands
    )
    assert runner.files[f"{op._run_dir(str(run_id), 'load')}/cancelled"] == (
        "1\n"
    )
    assert runner.files[f"{op._run_dir(str(run_id), 'train')}/cancelled"] == (
        "1\n"
    )
    assert any(
        command.startswith("rm -rf --")
        and f"{op._run_dir(str(run_id), 'load')}/env" in command
        for command in runner.commands
    )


def test_fetch_status_reconciles_dynamic_orchestration_job(monkeypatch):
    """Dynamic runs reconcile through the orchestration job metadata."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    run_dir = op._orchestration_run_dir(str(run_id))
    runner.files[f"{run_dir}/exit_code"] = "1\n"
    run = _run(
        run_id=run_id,
        run_metadata={SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY: "1000"},
    )

    pipeline_status, step_statuses = op.fetch_status(run, include_steps=True)

    assert pipeline_status is ExecutionStatus.FAILED
    assert step_statuses is None


def test_submit_isolated_step_publishes_job_metadata(monkeypatch):
    """Dynamic isolated steps are submitted as separate Slurm jobs."""
    op = _build_orchestrator()
    op.get_settings = lambda _info: SlurmOrchestratorSettings()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".orchestrator_utils.get_step_entrypoint_command",
        lambda **kwargs: (["python"], ["-m", "zenml.entrypoint"]),
    )
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".Stack.from_model",
        lambda stack: _stack(),
    )
    published_step_metadata = {}
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".publish_step_run_metadata",
        lambda **kwargs: published_step_metadata.update(kwargs),
    )
    published_run_metadata = {}

    class FakeClient:
        def create_run_metadata(self, **kwargs):
            published_run_metadata.update(kwargs)

    monkeypatch.setattr("zenml.client.Client", lambda: FakeClient())
    info = _isolated_step_info()

    op.submit_isolated_step(
        step_run_info=info,
        environment={"ZENML_STORE_API_KEY": SECRET_TOKEN},
    )

    run_dir = f"/runs/{info.run_id}/isolated/{info.step_run_id}"
    assert any(command.startswith("sbatch") for command in runner.commands)
    assert runner.modes[f"{run_dir}/env"] == 0o600
    assert SECRET_TOKEN in runner.files[f"{run_dir}/env"]
    assert info.step_run.run_metadata[SLURM_ISOLATED_JOB_ID_METADATA_KEY] == (
        "1000"
    )
    assert published_step_metadata == {
        "step_run_id": info.step_run_id,
        "step_run_metadata": {
            op.id: {SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1000"}
        },
    }
    assert published_run_metadata["metadata"] == {
        SLURM_ISOLATED_JOB_IDS_METADATA_KEY: {str(info.step_run_id): "1000"}
    }


def test_submit_isolated_step_cancels_on_run_metadata_failure(monkeypatch):
    """Run-level metadata publication is part of the submission transaction."""
    op = _build_orchestrator()
    op.get_settings = lambda _info: SlurmOrchestratorSettings()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".orchestrator_utils.get_step_entrypoint_command",
        lambda **kwargs: (["python"], ["-m", "zenml.entrypoint"]),
    )
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".Stack.from_model",
        lambda stack: _stack(),
    )
    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".publish_step_run_metadata",
        lambda **kwargs: None,
    )

    class FailingClient:
        def create_run_metadata(self, **kwargs):
            raise RuntimeError("metadata store unavailable")

    monkeypatch.setattr("zenml.client.Client", lambda: FailingClient())
    info = _isolated_step_info()

    with pytest.raises(RuntimeError, match="Failed to publish Slurm run"):
        op.submit_isolated_step(
            step_run_info=info,
            environment={"ZENML_STORE_API_KEY": SECRET_TOKEN},
        )

    run_dir = f"/runs/{info.run_id}/isolated/{info.step_run_id}"
    assert "scancel 1000" in runner.commands
    assert any(
        command.startswith("rm -rf --")
        and f"{run_dir}/env" in command
        for command in runner.commands
    )


def test_get_isolated_step_status_reads_sentinel(monkeypatch):
    """Isolated step status uses the same Slurm sentinel mapping."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    step_run_id = uuid4()
    run_dir = op._isolated_run_dir(str(run_id), str(step_run_id))
    runner.files[f"{run_dir}/exit_code"] = "0\n"
    step_run = SimpleNamespace(
        id=step_run_id,
        pipeline_run_id=run_id,
        run_metadata={SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1000"},
    )

    assert op.get_isolated_step_status(step_run) is ExecutionStatus.COMPLETED


def test_get_isolated_step_status_waits_for_missing_sentinel(monkeypatch):
    """A missing isolated sentinel gets a bounded retry window."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    step_run_id = uuid4()
    step_run = SimpleNamespace(
        id=step_run_id,
        pipeline_run_id=run_id,
        run_metadata={SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1000"},
    )

    assert (
        op.get_isolated_step_status(step_run)
        is ExecutionStatus.PROVISIONING
    )
    assert (
        op.get_isolated_step_status(step_run)
        is ExecutionStatus.PROVISIONING
    )
    assert op.get_isolated_step_status(step_run) is ExecutionStatus.FAILED


def test_get_isolated_step_status_normalizes_dynamic_runner_statuses(
    monkeypatch,
):
    """Isolated Slurm statuses use values supported by the dynamic monitor."""
    op = _build_orchestrator()

    class StatusRunner(FakeRunner):
        def __init__(self, state: str) -> None:
            """Initialize the fake.

            Args:
                state: Slurm state to return for the isolated job.
            """
            super().__init__()
            self.state = state

        def run(self, command: str) -> CommandResult:
            self.commands.append(command)
            if command.startswith("squeue"):
                return CommandResult(
                    exit_code=0,
                    stdout=f"1000|{self.state}\n",
                    stderr="",
                )
            return CommandResult(exit_code=0, stdout="", stderr="")

    run_id = uuid4()
    step_run_id = uuid4()
    step_run = SimpleNamespace(
        id=step_run_id,
        pipeline_run_id=run_id,
        run_metadata={SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1000"},
    )

    runner = StatusRunner("PENDING")
    _use_fake_client(monkeypatch, runner)
    assert (
        op.get_isolated_step_status(step_run)
        is ExecutionStatus.PROVISIONING
    )

    op._isolated_status_cache.clear()
    runner = StatusRunner("CANCELLED")
    _use_fake_client(monkeypatch, runner)
    assert op.get_isolated_step_status(step_run) is ExecutionStatus.STOPPED


def test_dynamic_monitor_keeps_pending_slurm_step(monkeypatch):
    """Pending Slurm jobs stay monitored and are not cleaned up early."""
    op = _build_orchestrator()

    class StatusRunner(FakeRunner):
        def run(self, command: str) -> CommandResult:
            self.commands.append(command)
            if command.startswith("squeue"):
                return CommandResult(
                    exit_code=0, stdout="1000|PENDING\n", stderr=""
                )
            return CommandResult(exit_code=0, stdout="", stderr="")

    runner = StatusRunner()
    _use_fake_client(monkeypatch, runner)
    step_run = SimpleNamespace(
        id=uuid4(),
        name="dynamic_train",
        pipeline_run_id=uuid4(),
        config=SimpleNamespace(step_operator=False),
        run_metadata={SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1000"},
    )

    dynamic_runner = DynamicPipelineRunner.__new__(DynamicPipelineRunner)
    dynamic_runner._shutdown_requested = False
    dynamic_runner._steps_to_monitor = {"dynamic_train": step_run}
    dynamic_runner._orchestrator = op
    dynamic_runner._step_operator = None
    cleaned_steps: List[object] = []
    dynamic_runner._cleanup_isolated_step = cleaned_steps.append

    class StopEvent:
        def wait(self, timeout: Optional[float] = None) -> None:
            """Stop the monitor after one pass.

            Args:
                timeout: Unused wait timeout.
            """
            _ = timeout
            dynamic_runner._shutdown_requested = True

        def clear(self) -> None:
            """No-op event clear."""

    dynamic_runner._monitoring_event = StopEvent()

    dynamic_runner._monitoring_loop()

    assert dynamic_runner._steps_to_monitor == {"dynamic_train": step_run}
    assert cleaned_steps == []


def test_get_isolated_step_status_batches_cached_run_jobs(monkeypatch):
    """Isolated step polling shares one Slurm state query per cache window."""
    op = _build_orchestrator()

    class StatusRunner(FakeRunner):
        def run(self, command: str) -> CommandResult:
            self.commands.append(command)
            if command.startswith("squeue"):
                return CommandResult(
                    exit_code=0,
                    stdout="1000|PENDING\n1001|RUNNING\n",
                    stderr="",
                )
            return CommandResult(exit_code=0, stdout="", stderr="")

    runner = StatusRunner()
    client_builds: List[SlurmClient] = []

    def build_client(config: SlurmOrchestratorConfig) -> SlurmClient:
        """Build a fake Slurm client and track connection churn.

        Args:
            config: Unused Slurm orchestrator config.

        Returns:
            A Slurm client backed by the fake runner.
        """
        _ = config
        client = SlurmClient(runner)
        client_builds.append(client)
        return client

    monkeypatch.setattr(
        "zenml.integrations.slurm.orchestrators.slurm_orchestrator"
        ".build_slurm_client",
        build_client,
    )
    run_id = uuid4()
    first_step = SimpleNamespace(
        id=uuid4(),
        pipeline_run_id=run_id,
        run_metadata={SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1000"},
    )
    second_step = SimpleNamespace(
        id=uuid4(),
        pipeline_run_id=run_id,
        run_metadata={SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1001"},
    )

    class FakeClient:
        def get_pipeline_run(self, *args, **kwargs):
            return _run(
                run_id=run_id,
                run_metadata={
                    SLURM_ISOLATED_JOB_IDS_METADATA_KEY: {
                        str(first_step.id): "1000",
                        str(second_step.id): "1001",
                    }
                },
            )

    monkeypatch.setattr("zenml.client.Client", lambda: FakeClient())

    assert (
        op.get_isolated_step_status(first_step)
        is ExecutionStatus.PROVISIONING
    )
    assert op.get_isolated_step_status(second_step) is ExecutionStatus.RUNNING
    assert [
        command for command in runner.commands if command.startswith("squeue")
    ] == ["squeue --noheader --format='%i|%T' --jobs=1000,1001"]
    assert len(client_builds) == 1


def test_stop_and_cleanup_isolated_step(monkeypatch):
    """Isolated step stop and cleanup address the step staging directory."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    run_id = uuid4()
    step_run_id = uuid4()
    step_run = SimpleNamespace(
        id=step_run_id,
        pipeline_run_id=run_id,
        run_metadata={SLURM_ISOLATED_JOB_ID_METADATA_KEY: "1000"},
    )

    op.stop_isolated_step(step_run)
    op.cleanup_isolated_step(step_run)

    run_dir = op._isolated_run_dir(str(run_id), str(step_run_id))
    assert "scancel 1000" in runner.commands
    assert runner.files[f"{run_dir}/cancelled"] == "1\n"
    assert any(
        command.startswith("rm -rf --")
        and f"{run_dir}/env" in command
        for command in runner.commands
    )
    assert any(
        command == f"rm -rf -- {run_dir}" for command in runner.commands
    )


def test_stop_run_cancels_dynamic_jobs(monkeypatch):
    """Stopping a dynamic run cancels orchestration and isolated jobs."""
    op = _build_orchestrator()
    runner = FakeRunner()
    _use_fake_client(monkeypatch, runner)
    monkeypatch.setattr(
        "zenml.orchestrators.base_orchestrator"
        ".publish_pipeline_run_status_update",
        lambda **kwargs: None,
    )
    run_id = uuid4()
    step_run_id = uuid4()
    run = SimpleNamespace(
        id=run_id,
        orchestrator_run_id=str(run_id),
        run_metadata={
            SLURM_ORCHESTRATION_JOB_ID_METADATA_KEY: "1000",
            SLURM_ISOLATED_JOB_IDS_METADATA_KEY: {str(step_run_id): "1001"},
        },
    )

    op.stop_run(run)

    assert "scancel 1001" in runner.commands
    assert "scancel 1000" in runner.commands
    assert (
        runner.files[
            f"{op._isolated_run_dir(str(run_id), str(step_run_id))}/cancelled"
        ]
        == "1\n"
    )
    assert (
        runner.files[f"{op._orchestration_run_dir(str(run_id))}/cancelled"]
        == "1\n"
    )
    assert any(
        command.startswith("rm -rf --")
        and f"{op._orchestration_run_dir(str(run_id))}/env" in command
        for command in runner.commands
    )


# --- validator ----------------------------------------------------------------


def test_validator_rejects_local_components():
    """The orchestrator needs a remote registry and artifact store."""
    op = _build_orchestrator()
    validator = op.validator
    assert validator is not None
    assert validator._required_components == {
        StackComponentType.CONTAINER_REGISTRY,
        StackComponentType.IMAGE_BUILDER,
    }
    check = validator._custom_validation_function
    assert check is not None

    def _stack(artifact_local: bool, registry_local: bool) -> SimpleNamespace:
        return SimpleNamespace(
            artifact_store=SimpleNamespace(
                name="a", config=SimpleNamespace(is_local=artifact_local)
            ),
            container_registry=SimpleNamespace(
                name="r", config=SimpleNamespace(is_local=registry_local)
            ),
        )

    assert check(_stack(True, False))[0] is False
    assert check(_stack(False, True))[0] is False
    assert check(_stack(False, False)) == (True, "")
