"""Check training control and exact sampling evidence without remote requests."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from training_client import EpisodeModel, TinkerPolicy


def policy() -> TinkerPolicy:
    """Create a policy without initialization or remote operations.

    Returns:
        Policy with local mock dependencies.
    """
    instance = object.__new__(TinkerPolicy)
    instance.failed = False
    instance.optimizer_steps = 0
    instance.max_tokens = 8
    instance.max_context = 32
    instance.temperature = 0.8
    instance.learning_rate = 1e-4
    instance.base_url = "http://127.0.0.1:8123"
    instance.trusted_service_host = None
    instance.api_key = "tml-local-skyrl"
    instance.tokenizer = Mock()
    instance.tokenizer.eos_token_id = 9
    instance.tokenizer.apply_chat_template.return_value = [1, 2, 3]
    instance.tokenizer.decode.return_value = "<action>done</action>"
    return instance


def sample() -> list[list[dict[str, Any]]]:
    """Build two samples from the same immutable checkpoint.

    Returns:
        One recorded turn per episode.
    """
    return [
        [
            {
                "prompt_ids": [1],
                "completion_ids": [2],
                "logprobs": [-0.5],
                "checkpoint": "snapshot-0",
            }
        ]
        for _ in range(2)
    ]


def test_equal_reward_skips_optimizer() -> None:
    """Avoid presenting zero-advantage groups as optimizer updates."""
    instance = policy()
    result = instance.update(sample(), [0.0, 0.0])
    assert result == {
        "updated": False,
        "reason": "all_rewards_equal",
        "optimizer_steps": 0,
    }


def test_cold_sampler_can_wait_longer_without_changing_later_defaults() -> (
    None
):
    """Cold inference initialization gets an explicit, finite wait budget."""
    instance = policy()
    instance.model_name = "test/model"
    instance.model_revision = "a" * 40
    instance.client = Mock()
    instance.client.save_weights_for_sampler.return_value.result.return_value = SimpleNamespace(
        path="tinker://model/before"
    )
    instance.service = Mock(create_sampling_client_async=AsyncMock())
    instance.snapshot("before", timeout=600)
    instance.client.save_weights_for_sampler.return_value.result.assert_called_with(
        timeout=600
    )
    instance.snapshot("later")
    instance.client.save_weights_for_sampler.return_value.result.assert_called_with(
        timeout=180
    )


@pytest.mark.parametrize("timeout", [0, 601, float("inf"), float("nan")])
def test_snapshot_rejects_unbounded_waits(timeout: float) -> None:
    """Invalid waits fail before a remote save is submitted.

    Args:
        timeout: Invalid sampler-save timeout.
    """
    with pytest.raises(ValueError, match="timeout"):
        policy().snapshot("before", timeout=timeout)


def test_mixed_checkpoints_are_rejected() -> None:
    """Prevent accidentally mixing stale and current-policy trajectories."""
    samples = sample()
    samples[1][0]["checkpoint"] = "another"
    with pytest.raises(ValueError, match="checkpoint"):
        policy().update(samples, [0.0, 1.0])


def test_uncertain_update_blocks_further_work() -> None:
    """Never retry an uncertain optimizer update through a new SDK request."""
    instance = policy()
    instance.failed = True
    with pytest.raises(RuntimeError, match="uncertain"):
        instance.update(sample(), [0.0, 1.0])


def test_sampling_keeps_exact_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Store sampled tokens directly instead of reconstructing decoded text.

    Args:
        monkeypatch: Scoped patch helper.
    """
    import sys

    fake = SimpleNamespace(
        ModelInput=SimpleNamespace(from_ints=lambda tokens: tokens),
        SamplingParams=lambda **kwargs: kwargs,
    )
    monkeypatch.setitem(sys.modules, "tinker", fake)
    client = Mock()
    client.sample.return_value.result.return_value = SimpleNamespace(
        sequences=[SimpleNamespace(tokens=[7, 8], logprobs=[-0.2, -0.3])]
    )
    model = EpisodeModel(
        policy(), {"client": client, "identity": {"path": "snapshot-0"}}
    )
    text, usage = model.complete(
        [{"role": "user", "content": "test"}], timeout=4
    )
    assert text == "<action>done</action>"
    assert model.samples[0]["completion_ids"] == [7, 8]
    assert model.samples[0]["logprobs"] == [-0.2, -0.3]
    assert usage["total_tokens"] == 5
    assert (
        model.policy.tokenizer.apply_chat_template.call_args.kwargs[
            "return_dict"
        ]
        is False
    )
    client.sample.return_value.result.assert_called_once_with(timeout=4)


def test_context_overflow_never_calls_sampler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject overlong conversations instead of silently changing their context.

    Args:
        monkeypatch: Scoped patch helper.
    """
    import sys

    monkeypatch.setitem(sys.modules, "tinker", SimpleNamespace())
    instance = policy()
    instance.max_context = 4
    client = Mock()
    with pytest.raises(ValueError, match="context"):
        EpisodeModel(instance, {"client": client}).complete([], timeout=3)
    client.sample.assert_not_called()


def test_export_uses_explicit_service_and_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep adapter exports attributable and separate from resumable state.

    Args:
        tmp_path: Temporary output directory.
        monkeypatch: Scoped patch helper.
    """
    import json

    instance = policy()
    monkeypatch.setattr(
        instance,
        "snapshot",
        lambda name: {
            "identity": {
                "path": "snapshot-final",
                "kind": "sampler_adapter_not_resume_checkpoint",
            }
        },
    )
    calls = []

    def download(args: list[str], **kwargs: Any) -> None:
        calls.append((args, kwargs))
        Path(args[-2], "adapter.safetensors").write_bytes(b"adapter")

    monkeypatch.setattr("training_client.subprocess.run", download)
    manifest = instance.download_checkpoint("final", tmp_path / "adapter")
    evidence = json.loads(manifest.read_text())
    assert evidence["kind"] == "sampler_adapter_not_resume_checkpoint"
    assert "adapter.safetensors" in evidence["files"]
    assert calls[0][0][-1] == instance.base_url
    assert calls[0][1]["timeout"] == 180
    assert calls[0][1]["env"]["TINKER_API_KEY"] == "tml-local-skyrl"


def test_official_cookbook_update_masks_nonappend_observations() -> None:
    """Exercise real Cookbook grouping, token masks, and optimizer dispatch."""
    from unittest.mock import AsyncMock

    pytest.importorskip("tinker_cookbook.rl.train")
    instance = policy()
    data_seen: list[Any] = []

    async def forward(data: list[Any], **kwargs: Any) -> Any:
        data_seen.extend(data)
        assert kwargs["loss_fn"] == "importance_sampling"
        return SimpleNamespace(
            result_async=AsyncMock(
                return_value=SimpleNamespace(
                    loss_fn_outputs=[
                        {"logprobs": datum.loss_fn_inputs["logprobs"]}
                        for datum in data
                    ]
                )
            )
        )

    instance.client = SimpleNamespace(
        forward_backward_async=AsyncMock(side_effect=forward),
        optim_step_async=AsyncMock(
            return_value=SimpleNamespace(
                result_async=AsyncMock(
                    return_value=SimpleNamespace(metrics={"grad_norm": 0.25})
                )
            )
        ),
    )
    samples = [
        [
            {
                "prompt_ids": [1, 2, 3],
                "completion_ids": [4],
                "logprobs": [-0.2],
                "checkpoint": "step-0",
            },
            {
                "prompt_ids": [8, 9],
                "completion_ids": [10],
                "logprobs": [-0.4],
                "checkpoint": "step-0",
            },
        ],
        [
            {
                "prompt_ids": [1],
                "completion_ids": [2],
                "logprobs": [-0.6],
                "checkpoint": "step-0",
            },
        ],
    ]
    result = instance.update(samples, [0.0, 1.0])
    assert result["updated"] is True
    assert result["advantages"] == [-0.5, 0.5]
    assert result["training_datums"] == 3
    assert result["metrics"]["grad_norm"] == 0.25
    instance.client.optim_step_async.assert_awaited_once()
    assert all("mask" not in datum.loss_fn_inputs for datum in data_seen)
    assert [
        datum.loss_fn_inputs["advantages"].to_torch().tolist()
        for datum in data_seen
    ] == [
        [0.0, 0.0, -0.5],
        [0.0, -0.5],
        [0.5],
    ]


def test_official_cookbook_failure_poisoning() -> None:
    """Do not submit another optimizer request after uncertain update failure."""
    from unittest.mock import AsyncMock

    pytest.importorskip("tinker_cookbook.rl.train")
    instance = policy()
    instance.client = SimpleNamespace(
        forward_backward_async=AsyncMock(
            side_effect=TimeoutError("uncertain")
        ),
        optim_step_async=AsyncMock(),
    )
    with pytest.raises(TimeoutError):
        instance.update(sample(), [0.0, 1.0])
    assert instance.failed
    with pytest.raises(RuntimeError, match="uncertain"):
        instance.update(sample(), [0.0, 1.0])
    instance.client.forward_backward_async.assert_awaited_once()
    instance.client.optim_step_async.assert_not_awaited()


def test_local_service_uses_explicit_placeholder_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not inherit a hosted-service key when connecting to local SkyRL.

    Args:
        monkeypatch: Scoped patch helper.
    """
    from unittest.mock import AsyncMock

    tinker = pytest.importorskip("tinker")
    transformers = pytest.importorskip("transformers")
    service = Mock()
    service.create_lora_training_client_async = AsyncMock(return_value=Mock())
    constructor = Mock(return_value=service)
    monkeypatch.setattr(tinker, "ServiceClient", constructor)
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", Mock())
    monkeypatch.setattr("training_client.subprocess.run", Mock())
    monkeypatch.setenv("TINKER_API_KEY", "synthetic-key-must-not-be-used")
    TinkerPolicy("http://127.0.0.1:8123", "model", "a" * 40)
    assert constructor.call_args.kwargs["api_key"] == "tml-local-skyrl"
    with pytest.raises(ValueError, match="local port-forward"):
        TinkerPolicy("https://remote.example", "model", "a" * 40)
    assert constructor.call_count == 1


def test_real_sdk_auth_and_session_against_loopback_server() -> None:
    """Exercise SDK auth validation and HTTP session creation without cloud calls."""
    import subprocess
    import sys

    pytest.importorskip("tinker")
    script = """
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import tinker

seen = []
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def respond(self):
        seen.append(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        if self.path.endswith("client/config"):
            data = {"use_pyqwest_transport": False}
        elif self.path.endswith("get_server_capabilities"):
            data = {"supported_models": [{"model_name": "/models/base"}]}
        elif self.path.endswith("create_session"):
            data = {"session_id": "local-session", "type": "create_session"}
        elif self.path.endswith("create_sampling_session"):
            data = {"sampling_session_id": "local-sampling", "type": "create_sampling_session"}
        elif self.path.endswith("session_heartbeat"):
            data = {}
        else:
            self.send_error(404)
            return
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_GET = respond
    do_POST = respond
server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    service = tinker.ServiceClient(base_url=f"http://127.0.0.1:{server.server_port}", api_key="tml-local-skyrl", timeout=3)
    capabilities = service.get_server_capabilities()
    assert capabilities.supported_models[0].model_name == "/models/base"
    sampler = service.create_sampling_client(base_model="/models/base")
    assert sampler is not None
    assert any(path.endswith("create_session") for path in seen), seen
    assert any(path.endswith("create_sampling_session") for path in seen), seen
finally:
    server.shutdown()
    server.server_close()
"""
    subprocess.run(
        [sys.executable, "-c", script],
        timeout=20,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("failure_kind", ["saved", "malformed", "timeout"])
def test_native_export_reports_safe_actionable_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_kind: str
) -> None:
    """Expose the child failure or deadline while suppressing credentials.

    Args:
        tmp_path: Checkpoint and diagnostic destination.
        monkeypatch: Scoped patch helper.
        failure_kind: Structured, malformed, or timed-out child failure.
    """
    import json
    import subprocess

    instance = policy()
    instance.trusted_service_host = "native-host"
    monkeypatch.setattr(
        instance, "snapshot", lambda name: {"identity": {"path": "final"}}
    )
    error_path = tmp_path / "checkpoint-download-error.json"
    error_path.write_text('{"type":"OldError","message":"stale failure"}')

    def fail(args: list[str], **kwargs: Any) -> None:
        assert kwargs["timeout"] == 420
        assert not error_path.exists()
        if failure_kind == "timeout":
            raise subprocess.TimeoutExpired(args, kwargs["timeout"])
        if failure_kind == "saved":
            error_path.write_text(
                json.dumps(
                    {
                        "type": "TimeoutError",
                        "message": f"read timed out {instance.api_key}",
                    }
                )
            )
        else:
            error_path.write_text("broken JSON")
        raise subprocess.CalledProcessError(1, args)

    monkeypatch.setattr("training_client.subprocess.run", fail)
    with pytest.raises(
        RuntimeError, match="Checkpoint export failed"
    ) as error:
        instance.download_checkpoint("final", tmp_path / "adapter")
    message = str(error.value)
    assert instance.api_key not in message
    assert "stale failure" not in message
    assert not (tmp_path / "adapter" / "manifest.json").exists()
    if failure_kind == "saved":
        assert "TimeoutError: read timed out [REDACTED]" in message
    elif failure_kind == "timeout":
        assert "420s export deadline" in message
    else:
        assert "download process failed" in message
