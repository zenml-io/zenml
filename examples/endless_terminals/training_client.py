"""Use official Tinker Cookbook policy-gradient updates with local episodes.

A timeout stops this controller from submitting further updates. It cannot undo
an optimizer request already accepted by the server; reconcile its checkpoint
and sequence state before starting another controller.
"""

import asyncio
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Awaitable
from urllib.parse import urlsplit


def validate_training_url(
    base_url: str, trusted_service_host: str | None = None
) -> None:
    """Restrict credentials to loopback or the exact owned service endpoint.

    Args:
        base_url: Training API origin.
        trusted_service_host: Exact DNS name provided by the native service.

    Raises:
        ValueError: The URL is not an allowed training origin.
    """
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError(
            "Training requires an HTTP(S) origin without credentials"
        )
    if trusted_service_host is None:
        if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError(
                "Training service must use a local port-forward URL"
            )
        return
    if (
        re.fullmatch(
            r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+modal\.host",
            trusted_service_host,
        )
        and parsed.hostname == trusted_service_host
        and parsed.scheme == "https"
        and parsed.port in {None, 443}
    ):
        return
    if (
        not re.fullmatch(
            r"endless-training-[0-9a-f]{16}\.[a-z0-9](?:[-a-z0-9]*[a-z0-9])?\.svc\.cluster\.local",
            trusted_service_host,
        )
        or parsed.hostname != trusted_service_host
        or parsed.port != 8001
    ):
        raise ValueError(
            "Training URL does not match the owned internal service"
        )


async def _wait(awaitable: Awaitable[Any], timeout: float) -> Any:
    """Await a remote operation within a controller deadline.

    Args:
        awaitable: SDK or Cookbook operation.
        timeout: Maximum waiting time in seconds.

    Returns:
        Completed operation result.
    """
    return await asyncio.wait_for(awaitable, timeout=timeout)


class EpisodeModel:
    """Adapt Tinker sampling to the existing terminal runner contract."""

    def __init__(
        self, policy: "TinkerPolicy", snapshot: dict[str, Any]
    ) -> None:
        """Keep one sampling checkpoint and exact per-turn training records.

        Args:
            policy: Policy settings and tokenizer.
            snapshot: Sampling client and immutable checkpoint identity.
        """
        self.policy = policy
        self.snapshot = snapshot
        self.samples: list[dict[str, Any]] = []

    def complete(
        self, messages: list[dict[str, str]], timeout: float
    ) -> tuple[str, dict[str, int]]:
        """Sample an action and retain token IDs before decoding for the parser.

        Args:
            messages: Existing terminal-runner conversation.
            timeout: Remaining per-call deadline.

        Returns:
            Decoded action and token usage.

        Raises:
            ValueError: Context budget or sampling evidence is invalid.
        """
        import tinker

        self.policy.ensure_available()
        prompt_ids = self.policy.tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=False,
        )
        if len(prompt_ids) + self.policy.max_tokens > self.policy.max_context:
            raise ValueError(
                "Training context budget exceeded; no silent truncation"
            )
        result = (
            self.snapshot["client"]
            .sample(
                prompt=tinker.ModelInput.from_ints(prompt_ids),
                num_samples=1,
                sampling_params=tinker.SamplingParams(
                    max_tokens=self.policy.max_tokens,
                    temperature=self.policy.temperature,
                    stop=[self.policy.tokenizer.eos_token_id],
                ),
            )
            .result(timeout=timeout)
        )
        sequence = result.sequences[0]
        tokens = list(sequence.tokens)
        logprobs = sequence.logprobs
        if not tokens or logprobs is None or len(tokens) != len(logprobs):
            raise ValueError(
                "Sampler must return one log probability per generated token"
            )
        if not all(math.isfinite(value) for value in logprobs):
            raise ValueError("Sampler returned nonfinite log probabilities")
        self.samples.append(
            {
                "prompt_ids": list(prompt_ids),
                "completion_ids": tokens,
                "logprobs": list(logprobs),
                "checkpoint": self.snapshot["identity"]["path"],
            }
        )
        usage = {
            "prompt_tokens": len(prompt_ids),
            "completion_tokens": len(tokens),
            "total_tokens": len(prompt_ids) + len(tokens),
        }
        return self.policy.tokenizer.decode(
            tokens, skip_special_tokens=True
        ), usage


class TinkerPolicy:
    """Train LoRA through pinned Tinker/Cookbook APIs without custom RL loss."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        model_revision: str,
        server_model: str = "/models/base",
        rank: int = 8,
        learning_rate: float = 1e-4,
        max_tokens: int = 512,
        temperature: float = 0.8,
        max_context: int = 8192,
        api_key: str = "tml-local-skyrl",
        trusted_service_host: str | None = None,
    ) -> None:
        """Connect to an explicitly configured private training service.

        Args:
            base_url: Loopback or authenticated internal SkyRL service URL.
            model_name: Hugging Face tokenizer/model identity.
            model_revision: Immutable tokenizer/model revision.
            server_model: Pinned model location on the training server.
            rank: LoRA rank.
            learning_rate: Adam learning rate.
            max_tokens: Generated tokens per terminal response.
            temperature: Sampling temperature.
            max_context: Total prompt plus completion token limit.
            api_key: API credential, kept out of public training evidence.
            trusted_service_host: Exact native service DNS name, if applicable.

        Raises:
            ValueError: Settings are invalid.
        """
        import tinker
        from transformers import AutoTokenizer

        if (
            not base_url
            or rank <= 0
            or learning_rate <= 0
            or not 0 < max_tokens < max_context
        ):
            raise ValueError("Invalid bounded training configuration")
        if len(model_revision) != 40 or any(
            c not in "0123456789abcdef" for c in model_revision
        ):
            raise ValueError("Use an immutable 40-character model revision")
        validate_training_url(base_url, trusted_service_host)
        if not api_key or (
            trusted_service_host is not None
            and not re.fullmatch(r"tml-native-[0-9a-f]{64}", api_key)
        ):
            raise ValueError("Native training requires its per-run API key")
        self.base_url = base_url
        self.api_key = api_key
        self.trusted_service_host = trusted_service_host
        self.model_name = model_name
        self.model_revision = model_revision
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_context = max_context
        self.learning_rate = learning_rate
        self.optimizer_steps = 0
        self.failed = False
        self.service = tinker.ServiceClient(
            base_url=base_url, api_key=api_key, timeout=60.0
        )
        self.client = asyncio.run(
            _wait(
                self.service.create_lora_training_client_async(
                    base_model=server_model, rank=rank
                ),
                600,
            )
        )
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; from transformers import AutoTokenizer; "
                "AutoTokenizer.from_pretrained(sys.argv[1], revision=sys.argv[2])",
                model_name,
                model_revision,
            ],
            timeout=180,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, revision=model_revision, local_files_only=True
        )

    def ensure_available(self) -> None:
        """Prevent subsequent training after an uncertain remote update.

        Raises:
            RuntimeError: An earlier update failed or timed out.
        """
        if self.failed:
            raise RuntimeError(
                "Training state is uncertain; reconcile before resuming"
            )

    def snapshot(self, name: str, *, timeout: float = 180) -> dict[str, Any]:
        """Save sampler weights and return their sampling client and identity.

        Args:
            name: Unique checkpoint name.
            timeout: Maximum wait for saving sampler weights, in seconds.

        Returns:
            Sampling handle with serializable identity in its identity field.

        Raises:
            ValueError: The timeout is outside the bounded supported range.
        """
        if not 0 < timeout <= 600:
            raise ValueError("Sampler snapshot timeout must be in (0, 600]")
        self.ensure_available()
        saved = self.client.save_weights_for_sampler(name).result(
            timeout=timeout
        )
        sampler = asyncio.run(
            _wait(
                self.service.create_sampling_client_async(
                    model_path=saved.path
                ),
                60,
            )
        )
        return {
            "client": sampler,
            "identity": {
                "path": saved.path,
                "model_name": self.model_name,
                "model_revision": self.model_revision,
                "optimizer_steps": self.optimizer_steps,
                "kind": "sampler_adapter_not_resume_checkpoint",
            },
        }

    def episode_model(self, snapshot: dict[str, Any]) -> EpisodeModel:
        """Build an independent episode recorder for the given checkpoint.

        Args:
            snapshot: Snapshot returned by this policy.

        Returns:
            Terminal-runner-compatible model with public samples.
        """
        return EpisodeModel(self, snapshot)

    def update(
        self, group_samples: list[list[dict[str, Any]]], rewards: list[float]
    ) -> dict[str, Any]:
        """Run one official group-relative policy-gradient optimizer update.

        Args:
            group_samples: Per-episode turns sampled from the same checkpoint/task.
            rewards: Explicit controller-calculated reward for each episode.

        Returns:
            Update status, group advantages, and official optimizer metrics.

        Raises:
            ValueError: Group evidence is incomplete or mixes checkpoints.
            BaseException: The remote update fails or exceeds its deadline.
        """
        self.ensure_available()
        if (
            len(group_samples) != len(rewards)
            or len(rewards) < 2
            or not all(group_samples)
        ):
            raise ValueError(
                "Need at least two nonempty episodes and matching rewards"
            )
        if not all(math.isfinite(value) for value in rewards):
            raise ValueError("Rewards must be finite")
        checkpoints = {
            sample["checkpoint"]
            for episode in group_samples
            for sample in episode
        }
        if len(checkpoints) != 1:
            raise ValueError("An update must use one sampling checkpoint")
        if len(set(rewards)) == 1:
            return {
                "updated": False,
                "reason": "all_rewards_equal",
                "optimizer_steps": self.optimizer_steps,
            }
        import tinker
        from tinker_cookbook.completers import TokensWithLogprobs
        from tinker_cookbook.rl.data_processing import (
            assemble_training_data,
            compute_advantages,
        )
        from tinker_cookbook.rl.train import train_step
        from tinker_cookbook.rl.types import (
            Trajectory,
            TrajectoryGroup,
            Transition,
        )

        trajectories = []
        for samples in group_samples:
            transitions = [
                Transition(
                    ob=tinker.ModelInput.from_ints(sample["prompt_ids"]),
                    ac=TokensWithLogprobs(
                        tokens=sample["completion_ids"],
                        maybe_logprobs=sample["logprobs"],
                    ),
                    reward=0.0,
                    episode_done=index == len(samples) - 1,
                )
                for index, sample in enumerate(samples)
            ]
            trajectories.append(
                Trajectory(
                    transitions=transitions,
                    final_ob=tinker.ModelInput.from_ints([]),
                )
            )
        groups = [
            TrajectoryGroup(
                trajectories_G=trajectories,
                final_rewards_G=rewards,
                metrics_G=[{} for _ in rewards],
            )
        ]
        advantages = compute_advantages(groups)
        data, _ = assemble_training_data(groups, advantages)
        metrics: dict[str, Any] = {}
        try:
            asyncio.run(
                _wait(
                    train_step(
                        data_D=data,
                        training_client=self.client,
                        learning_rate=self.learning_rate,
                        num_substeps=1,
                        loss_fn="importance_sampling",
                        metrics=metrics,
                    ),
                    300,
                )
            )
        except BaseException:
            self.failed = True
            raise
        self.optimizer_steps += 1
        return {
            "updated": True,
            "optimizer_steps": self.optimizer_steps,
            "advantages": advantages[0].tolist(),
            "metrics": metrics,
            "training_datums": len(data),
        }

    def download_checkpoint(self, name: str, directory: Path) -> Path:
        """Download sampler-only adapter files and write their provenance hashes.

        Args:
            name: New sampler checkpoint name.
            directory: New local artifact directory.

        Returns:
            Manifest path identifying downloaded adapter files, not optimizer state.

        Raises:
            RuntimeError: The checkpoint export failed or contains no files.
        """
        self.ensure_available()
        directory.mkdir(parents=True, exist_ok=False)
        snapshot = self.snapshot(name)
        command = (
            [
                sys.executable,
                str(Path(__file__).with_name("checkpoint_download.py")),
                snapshot["identity"]["path"],
                str(directory.resolve()),
                self.base_url,
            ]
            if self.trusted_service_host is not None
            else [
                sys.executable,
                "-c",
                "import sys; from tinker_cookbook import weights; "
                "weights.download(tinker_path=sys.argv[1], output_dir=sys.argv[2], base_url=sys.argv[3])",
                snapshot["identity"]["path"],
                str(directory.resolve()),
                self.base_url,
            ]
        )
        error_path = directory.parent / "checkpoint-download-error.json"
        error_path.unlink(missing_ok=True)
        export_timeout = 420 if self.trusted_service_host is not None else 180
        try:
            subprocess.run(
                command,
                env={**os.environ, "TINKER_API_KEY": self.api_key},
                timeout=export_timeout,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ) as error:
            detail = (
                f"exceeded the {export_timeout}s export deadline"
                if isinstance(error, subprocess.TimeoutExpired)
                else "download process failed"
            )
            try:
                saved = json.loads(error_path.read_text())
                if (
                    isinstance(saved, dict)
                    and isinstance(saved.get("type"), str)
                    and isinstance(saved.get("message"), str)
                ):
                    detail = f"{saved['type']}: {saved['message']}"
            except (OSError, ValueError):
                pass
            detail = detail.replace(self.api_key, "[REDACTED]")[:4096]
            raise RuntimeError(f"Checkpoint export failed: {detail}") from None
        hashes = {
            str(path.relative_to(directory)): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(directory.rglob("*"))
            if path.is_file()
        }
        if not hashes:
            raise RuntimeError("Checkpoint export returned no files")
        manifest = directory / "manifest.json"
        manifest.write_text(
            json.dumps({**snapshot["identity"], "files": hashes}, indent=2)
            + "\n"
        )
        return manifest
