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
"""Unit tests for the SSH orchestrator.

These tests mock the SSH connection (``SSHClient``) and ``subprocess`` so
they cover the wiring — static Compose-DAG generation, the dynamic
orchestrator-container launch, and subprocess-based isolated steps — without
a live remote host.
"""

from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import yaml

from zenml.enums import ExecutionMode, ExecutionStatus, StackComponentType
from zenml.integrations.ssh.flavors.ssh_orchestrator_flavor import (
    SSHOrchestratorConfig,
    SSHOrchestratorFlavor,
    SSHOrchestratorSettings,
)
from zenml.integrations.ssh.orchestrators.ssh_orchestrator import (
    ENV_ZENML_SSH_RUN_ID,
    SSHOrchestrator,
)

_MODULE = "zenml.integrations.ssh.orchestrators.ssh_orchestrator"


def _make_orchestrator(**config_overrides: Any) -> SSHOrchestrator:
    cfg = SSHOrchestratorConfig(
        hostname="gpu-box",
        username="ubuntu",
        ssh_key_path="~/.ssh/id_ed25519",
        **config_overrides,
    )
    return SSHOrchestrator(
        name="ssh",
        id=uuid4(),
        config=cfg,
        flavor="ssh",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created="2026-01-01T00:00:00",
        updated="2026-01-01T00:00:00",
    )


def _fake_step(upstream: Any = ()) -> MagicMock:
    step = MagicMock()
    step.spec.upstream_steps = list(upstream)
    return step


def _fake_snapshot(steps: dict) -> MagicMock:
    snap = MagicMock()
    snap.id = uuid4()
    snap.step_configurations = steps
    return snap


@contextmanager
def _patched_ssh() -> Iterator[MagicMock]:
    """Patch SSHClient; yield the entered client mock for assertions."""
    with patch(f"{_MODULE}.SSHClient") as ssh_cls:
        client = MagicMock()
        client.exec.return_value = MagicMock(exit_code=0, stdout="", stderr="")
        ssh_cls.return_value.__enter__.return_value = client
        yield client


class TestFlavor:
    def test_flavor_metadata(self) -> None:
        f = SSHOrchestratorFlavor()
        assert f.name == "ssh"
        assert f.config_class is SSHOrchestratorConfig
        assert f.implementation_class is SSHOrchestrator

    def test_auth_validator_requires_a_key(self) -> None:
        with pytest.raises(ValueError, match="ssh_key_path"):
            SSHOrchestratorConfig(hostname="h", username="u")

    def test_is_remote(self) -> None:
        assert _make_orchestrator().config.is_remote is True

    def test_validator_requires_registry_and_builder(self) -> None:
        required = _make_orchestrator().validator._required_components
        assert StackComponentType.CONTAINER_REGISTRY in required
        assert StackComponentType.IMAGE_BUILDER in required

    def test_supports_all_execution_modes(self) -> None:
        modes = _make_orchestrator().supported_execution_modes()
        assert ExecutionMode.FAIL_FAST in modes
        assert ExecutionMode.STOP_ON_FAILURE in modes
        assert ExecutionMode.CONTINUE_ON_FAILURE in modes


class TestStaticSubmit:
    def _submit(self, orch: SSHOrchestrator, snapshot: MagicMock) -> dict:
        """Run submit_pipeline and return the parsed Compose dict."""
        run = MagicMock()
        run.id = uuid4()
        with (
            _patched_ssh() as ssh,
            patch.object(orch, "get_image", return_value="img:latest"),
            patch.object(
                orch, "get_settings", return_value=SSHOrchestratorSettings()
            ),
        ):
            orch.submit_pipeline(
                snapshot=snapshot,
                stack=MagicMock(),
                base_environment={},
                step_environments={
                    name: {"FOO": "bar"}
                    for name in snapshot.step_configurations
                },
                placeholder_run=run,
            )
        # find the put_text(...docker-compose.yml..., yaml) call
        compose_yaml = next(
            call.args[1]
            for call in ssh.put_text.call_args_list
            if call.args[0].endswith("docker-compose.yml")
        )
        return yaml.safe_load(compose_yaml)

    def test_one_service_per_step_with_edges(self) -> None:
        orch = _make_orchestrator()
        snap = _fake_snapshot(
            {"load": _fake_step(), "train": _fake_step(upstream=["load"])}
        )
        compose = self._submit(orch, snap)
        services = compose["services"]
        assert len(services) == 2
        train = services[f"{snap.id}-train"]
        # depends_on edge from train -> load with completion condition
        assert train["depends_on"] == {
            f"{snap.id}-load": {"condition": "service_completed_successfully"}
        }
        # run-id env injected + step env carried through
        assert train["environment"][ENV_ZENML_SSH_RUN_ID]
        assert train["environment"]["FOO"] == "bar"
        # GPU reservation present by default
        assert train["deploy"]["resources"]["reservations"]["devices"]

    def test_compose_up_invoked(self) -> None:
        orch = _make_orchestrator()
        snap = _fake_snapshot({"only": _fake_step()})
        run = MagicMock()
        run.id = uuid4()
        with (
            _patched_ssh() as ssh,
            patch.object(orch, "get_image", return_value="img"),
            patch.object(
                orch, "get_settings", return_value=SSHOrchestratorSettings()
            ),
        ):
            orch.submit_pipeline(
                snapshot=snap,
                stack=MagicMock(),
                base_environment={},
                step_environments={"only": {}},
                placeholder_run=run,
            )
        assert any(
            "compose up -d" in call.args[0] for call in ssh.exec.call_args_list
        )


class TestDynamicSubmit:
    def test_single_orchestrator_service(self) -> None:
        orch = _make_orchestrator()
        snap = _fake_snapshot({"a": _fake_step(), "b": _fake_step()})
        run = MagicMock()
        run.id = uuid4()
        with (
            _patched_ssh() as ssh,
            patch.object(orch, "get_image", return_value="orch-img"),
        ):
            orch.submit_dynamic_pipeline(
                snapshot=snap,
                stack=MagicMock(),
                environment={"ZENML_STORE_URL": "x"},
                placeholder_run=run,
            )
        compose_yaml = next(
            call.args[1]
            for call in ssh.put_text.call_args_list
            if call.args[0].endswith("docker-compose.yml")
        )
        compose = yaml.safe_load(compose_yaml)
        # exactly one service that runs the orchestrator image
        assert list(compose["services"]) == ["orchestrator"]
        svc = compose["services"]["orchestrator"]
        assert svc["image"] == "orch-img"
        assert svc["environment"][ENV_ZENML_SSH_RUN_ID]

    def test_supports_dynamic_and_isolated_flags(self) -> None:
        orch = _make_orchestrator()
        # Overriding these methods flips the capability flags ZenML checks
        # (they are properties computed via introspection).
        assert orch.supports_dynamic_pipelines is True
        assert orch.can_run_isolated_steps is True
        assert orch.can_stop_isolated_steps is True


def _fake_step_run_info() -> MagicMock:
    info = MagicMock()
    info.pipeline_step_name = "train"
    info.step_run_id = uuid4()
    info.snapshot.id = uuid4()
    return info


class TestIsolatedStepSubprocess:
    def test_submit_uses_subprocess_not_thread(self) -> None:
        orch = _make_orchestrator()
        info = _fake_step_run_info()
        with (
            patch(
                f"{_MODULE}.orchestrator_utils.get_step_entrypoint_command",
                return_value=(["python", "-m", "x"], ["--step_name", "train"]),
            ),
            patch(f"{_MODULE}.subprocess.Popen") as popen,
            patch(f"{_MODULE}.threading.Thread") as thread,
        ):
            popen.return_value = MagicMock()
            orch.submit_isolated_step(info, {"E": "1"})
        popen.assert_called_once()
        thread.assert_not_called()
        # process registered by step_run_id
        assert info.step_run_id in orch._step_procs
        # start_new_session for clean process-group kill
        assert popen.call_args.kwargs.get("start_new_session") is True

    def test_status_maps_poll_codes(self) -> None:
        orch = _make_orchestrator()
        step_run = MagicMock()
        step_run.id = uuid4()
        proc = MagicMock()
        orch._step_procs[step_run.id] = proc

        proc.poll.return_value = None
        assert orch.get_isolated_step_status(step_run) == (
            ExecutionStatus.RUNNING
        )
        proc.poll.return_value = 0
        assert orch.get_isolated_step_status(step_run) == (
            ExecutionStatus.COMPLETED
        )
        proc.poll.return_value = 3
        assert orch.get_isolated_step_status(step_run) == (
            ExecutionStatus.FAILED
        )

    def test_status_unknown_step_falls_back_to_running(self) -> None:
        orch = _make_orchestrator()
        step_run = MagicMock()
        step_run.id = uuid4()  # never submitted
        assert orch.get_isolated_step_status(step_run) == (
            ExecutionStatus.RUNNING
        )

    def test_stop_kills_process_group(self) -> None:
        orch = _make_orchestrator()
        step_run = MagicMock()
        step_run.id = uuid4()
        proc = MagicMock()
        proc.poll.return_value = None
        proc.pid = 4321
        orch._step_procs[step_run.id] = proc
        with (
            patch(f"{_MODULE}.os.getpgid", return_value=4321) as getpgid,
            patch(f"{_MODULE}.os.killpg") as killpg,
        ):
            orch.stop_isolated_step(step_run)
        getpgid.assert_called_once_with(4321)
        killpg.assert_called_once()

    def test_stop_noop_for_finished_step(self) -> None:
        orch = _make_orchestrator()
        step_run = MagicMock()
        step_run.id = uuid4()
        proc = MagicMock()
        proc.poll.return_value = 0  # already exited
        orch._step_procs[step_run.id] = proc
        with patch(f"{_MODULE}.os.killpg") as killpg:
            orch.stop_isolated_step(step_run)
        killpg.assert_not_called()
