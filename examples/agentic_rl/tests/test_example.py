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
"""Tests of the example's steps and committed assets.

Run from the example dir with its venv:  pytest tests/ -q
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

EXAMPLE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(EXAMPLE_DIR))

from steps.gate import gate_train_readiness  # noqa: E402
from steps.ingest_rollout_traces import ingest_rollout_traces  # noqa: E402
from steps.serve import (  # noqa: E402
    probe_policy_service,
    serve_checkpoint,
    stop_policy_service,
)


@pytest.fixture(autouse=True)
def _no_step_metadata(monkeypatch):
    """Steps call log_metadata, which needs an active step context.

    Patched via sys.modules: in the package namespace the step objects
    shadow their modules, so string-based monkeypatch resolution would
    hit the step instead of the module.
    """
    monkeypatch.setattr(
        sys.modules["steps.gate"], "log_metadata", lambda **kwargs: None
    )
    monkeypatch.setattr(
        sys.modules["steps.ingest_rollout_traces"],
        "log_metadata",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        sys.modules["steps.serve"], "log_metadata", lambda **kwargs: None
    )
    # Server-side registration is best-effort bookkeeping; default it to a
    # stub so no test accidentally reaches a real ZenML server. Tests that
    # assert on registration install their own client.
    monkeypatch.setattr(
        sys.modules["steps.serve"], "Client", lambda: mock.MagicMock()
    )


def _shard(n_total=2, n_errored=0, rewards=(1.0, 0.0)):
    """Fake HarborShardResult carrying just what the gate reads.

    Args:
        n_total: Total trials in the shard.
        n_errored: Errored trials in the shard.
        rewards: One reward per non-errored trial.

    Returns:
        A shard-result stand-in.
    """
    trials = [
        SimpleNamespace(rewards={"solved": reward}) for reward in rewards
    ]
    trials += [SimpleNamespace(rewards=None)] * n_errored
    return SimpleNamespace(
        n_total_trials=n_total, n_errored=n_errored, trials=trials
    )


class TestGate:
    def test_passes_midwindow(self) -> None:
        verdict = gate_train_readiness.entrypoint(
            results=[_shard(rewards=(1.0, 0.0))]
        )
        assert verdict["passed"] is True
        assert verdict["mean_reward"] == 0.5

    def test_errors_checked_before_rewards(self) -> None:
        """An errored trial fails the gate even with a healthy mean.

        Errored shards log no mean reward, so a reward-only gate reads
        a broken campaign as passing — the ordering is the feature.
        """
        with pytest.raises(RuntimeError, match="ERRORED"):
            gate_train_readiness.entrypoint(
                results=[_shard(n_total=3, n_errored=1, rewards=(0.5, 0.5))]
            )

    def test_no_rewards_fails(self) -> None:
        with pytest.raises(RuntimeError, match="no trial produced"):
            gate_train_readiness.entrypoint(
                results=[_shard(n_total=1, n_errored=0, rewards=())]
            )

    def test_saturation_fails(self) -> None:
        with pytest.raises(RuntimeError, match="saturated"):
            gate_train_readiness.entrypoint(
                results=[_shard(rewards=(1.0, 1.0))]
            )

    def test_broken_env_floor_fails(self) -> None:
        with pytest.raises(RuntimeError, match="broken or"):
            gate_train_readiness.entrypoint(
                results=[_shard(rewards=(0.0, 0.0))]
            )


def _write_trace(path: Path, **overrides) -> None:
    """Append one minimal Rollout record to a traces.jsonl file.

    Args:
        path: The traces.jsonl path.
        overrides: Record field overrides.
    """
    record = {
        "id": "trace-1",
        "env_name": "zenml-pipeline-writing",
        "group_id": "g-1",
        "policy_version": 3,
        "rewards": {"sandbox_scored": 0.7},
        "metrics": {"infra_error": 0.0},
        "runtime": {"type": "zenml", "id": "docker-abc123"},
        "task": {"data": {"name": "const_seven"}},
        "nodes": [{}, {}],
        "is_completed": True,
        "stop_condition": None,
        "errors": [],
        "info": {},
        "timing": {"start": 123.0},
    }
    record.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(record) + "\n")


class TestIngest:
    def test_ingests_rollouts_with_sandbox_join(self, tmp_path) -> None:
        base = tmp_path / "rollouts" / "step_1" / "train" / "all"
        _write_trace(base / "traces.jsonl")
        _write_trace(
            base / "traces.jsonl",
            id="trace-2",
            rewards={"sandbox_scored": 0.1},
        )
        table = ingest_rollout_traces.entrypoint(
            output_dir=str(tmp_path), expected_min_rollouts=2
        )
        assert len(table) == 2
        assert set(table["runtime_id"]) == {"docker-abc123"}
        assert table["reward"].tolist() == [0.7, 0.1]
        assert table["train_step"].tolist() == [1, 1]

    def test_partial_ingest_fails_loudly(self, tmp_path) -> None:
        base = tmp_path / "rollouts" / "step_1" / "train" / "all"
        _write_trace(base / "traces.jsonl")
        with pytest.raises(RuntimeError, match="Refusing to record"):
            ingest_rollout_traces.entrypoint(
                output_dir=str(tmp_path), expected_min_rollouts=5
            )

    def test_missing_rollout_dir_fails(self, tmp_path) -> None:
        with pytest.raises(RuntimeError, match="No traces.jsonl"):
            ingest_rollout_traces.entrypoint(output_dir=str(tmp_path))

    def test_eval_layout_via_custom_glob(self, tmp_path) -> None:
        """verifiers eval outputs share the schema, not the layout."""
        _write_trace(
            tmp_path / "taskset--model--default" / "uuid1" / "traces.jsonl"
        )
        table = ingest_rollout_traces.entrypoint(
            output_dir=str(tmp_path), traces_glob="**/traces.jsonl"
        )
        assert len(table) == 1
        assert table["train_step"].iloc[0] == -1
        assert table["runtime_id"].iloc[0] == "docker-abc123"

    def test_infra_error_column_surfaces(self, tmp_path) -> None:
        base = tmp_path / "rollouts" / "step_2" / "train" / "all"
        _write_trace(
            base / "traces.jsonl",
            rewards={},
            info={"infra_error": "scorer exited 1"},
        )
        table = ingest_rollout_traces.entrypoint(output_dir=str(tmp_path))
        assert table["infra_error"].iloc[0] == "scorer exited 1"


@pytest.fixture(scope="session", autouse=True)
def _generated_taskset():
    """Generate the taskset once if absent (it is gitignored)."""
    if not (EXAMPLE_DIR / "tasks").is_dir():
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "gen_taskset", EXAMPLE_DIR / "scripts" / "gen_taskset.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.main()


class TestCommittedAssets:
    def test_scorer_copy_is_byte_identical(self) -> None:
        """The 'verbatim scorer' claim, asserted.

        The source of truth lives in the RL spike branch; on checkouts
        without it, the committed copy is the canonical scorer and
        there is nothing to compare against.
        """
        source = (
            EXAMPLE_DIR.parent
            / "rl_spike"
            / "sandbox_scripts"
            / "score_pipeline.py"
        )
        if not source.exists():
            pytest.skip("rl_spike source tree not present on this branch")
        copy = EXAMPLE_DIR / "docker" / "score_pipeline.py"
        assert copy.read_bytes() == source.read_bytes()

    def test_all_tasks_pin_the_scorer_image(self) -> None:
        task_dirs = [
            path for path in (EXAMPLE_DIR / "tasks").iterdir() if path.is_dir()
        ]
        assert len(task_dirs) == 64
        for task_dir in task_dirs:
            toml_text = (task_dir / "task.toml").read_text()
            assert 'docker_image = "zenml-rl-scorer:0.1"' in toml_text
            assert (task_dir / "tests" / "test.sh").exists()
            assert (task_dir / "tests" / "spec.json").exists()

    def test_oracle_solutions_only_for_mechanical_specs(self) -> None:
        for task_dir in (EXAMPLE_DIR / "tasks").iterdir():
            if not task_dir.is_dir():
                continue
            spec = json.loads((task_dir / "tests" / "spec.json").read_text())
            has_solution = (task_dir / "solution" / "solve.sh").exists()
            mechanical = not (
                set(spec) - {"min_steps", "expected_output"}
            ) and "value" in spec.get("expected_output", {})
            assert has_solution == mechanical, task_dir.name

    def test_smoke_task_ids_have_solutions(self) -> None:
        from run import SMOKE_TASK_IDS

        for task_id in SMOKE_TASK_IDS:
            assert (
                EXAMPLE_DIR / "tasks" / task_id / "solution" / "solve.sh"
            ).exists(), task_id


class _ModelsHandler(BaseHTTPRequestHandler):
    """Answer any GET with a vLLM-shaped /v1/models payload."""

    def do_GET(self) -> None:  # noqa: N802
        body = json.dumps(
            {"object": "list", "data": [{"id": "policy"}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:  # noqa: A002
        """Silence the default request logging."""


def _fake_service(name: str = "policy") -> SimpleNamespace:
    """A service stand-in exposing what the registration helpers read.

    Args:
        name: The service name, echoed into ``config.service_name``.

    Returns:
        A duck-typed service handle.
    """
    return SimpleNamespace(
        stop=lambda timeout=120: None,
        SERVICE_TYPE="k8s",
        admin_state="active",
        config=SimpleNamespace(service_name=f"zenml-endpoint-{name}"),
        status=SimpleNamespace(model_dump=lambda: {"state": "active"}),
        endpoint=SimpleNamespace(model_dump=lambda: {"url": "http://x"}),
        model_dump=lambda: {"type": "steps.serve.Fake"},
    )


class TestServe:
    def test_serve_without_checkpoint_raises(self) -> None:
        """No checkpoint => the trainer ran without --ckpt: fail loud.

        The None check fires before the lazy kubernetes import, so this
        runs without the k8s extra installed.
        """
        with pytest.raises(RuntimeError, match="Nothing to serve"):
            serve_checkpoint.entrypoint(checkpoint_dir=None, image="vllm:x")

    def test_probe_reaches_local_endpoint(self) -> None:
        """The probe reads only .url and reports a reachable endpoint.

        A SimpleNamespace stands in for the service — the probe
        duck-types on ``.url`` and never touches the concrete class.
        """
        server = HTTPServer(("127.0.0.1", 0), _ModelsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            stub = SimpleNamespace(
                url=f"http://127.0.0.1:{server.server_address[1]}"
            )
            result = probe_policy_service.entrypoint(service=stub)
        finally:
            server.shutdown()
            thread.join()
        assert result["reachable"] is True
        assert result["models"] == ["policy"]
        assert result["latency_seconds"] is not None

    def test_probe_unreachable_endpoint_is_recorded_not_raised(self) -> None:
        """An unreachable endpoint is a recorded fact, never an exception."""
        # Port 1 is privileged and unused — the connection is refused fast.
        stub = SimpleNamespace(url="http://127.0.0.1:1")
        result = probe_policy_service.entrypoint(service=stub)
        assert result["reachable"] is False
        assert result["latency_seconds"] is None
        assert "error" in result

    def test_stop_never_raises_even_when_teardown_explodes(self) -> None:
        """Teardown must not mask the run's outcome — swallow and warn."""

        def _explode(*args, **kwargs) -> None:
            raise RuntimeError("pod delete failed")

        stub = SimpleNamespace(stop=_explode)
        stop_policy_service.entrypoint(service=stub)

    def test_registration_called_on_happy_path(self, monkeypatch) -> None:
        """An ACTIVE service is registered with the ZenML server."""
        serve_module = sys.modules["steps.serve"]
        client = mock.MagicMock()
        client.create_service.return_value = SimpleNamespace(id="svc-id")
        monkeypatch.setattr(serve_module, "Client", lambda: client)

        serve_module._register_policy_service(_fake_service())

        client.create_service.assert_called_once()
        client.update_service.assert_called_once()
        assert client.update_service.call_args.kwargs["id"] == "svc-id"

    def test_registration_failure_does_not_raise(self, monkeypatch) -> None:
        """Serving already succeeded; a failed registration is swallowed."""
        serve_module = sys.modules["steps.serve"]
        client = mock.MagicMock()
        client.create_service.side_effect = RuntimeError("no server")
        monkeypatch.setattr(serve_module, "Client", lambda: client)

        serve_module._register_policy_service(_fake_service())

    def test_stop_updates_record_best_effort(self, monkeypatch) -> None:
        """After teardown the tracked record is updated by name."""
        serve_module = sys.modules["steps.serve"]
        client = mock.MagicMock()
        client.get_service.return_value = SimpleNamespace(id="svc-id")
        monkeypatch.setattr(serve_module, "Client", lambda: client)

        stop_policy_service.entrypoint(service=_fake_service())

        client.get_service.assert_called_once()
        client.update_service.assert_called_once()
        assert client.update_service.call_args.kwargs["id"] == "svc-id"
