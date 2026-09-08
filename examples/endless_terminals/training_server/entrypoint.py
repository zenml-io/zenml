"""Download immutable weights before starting the local training API."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

CHECKPOINTS = Path("/checkpoints")
MODEL_PATH = Path("/models/base")
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"


def main() -> None:
    """Start SkyRL using a pinned model snapshot and persisted API state.

    Raises:
        ValueError: The revision is mutable or the stable model path is not a symlink.
    """
    model = os.environ.get("SKYRL_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")
    revision = os.environ.get("SKYRL_MODEL_REVISION", MODEL_REVISION)
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("SKYRL_MODEL_REVISION must be a 40-character commit")
    checkpoints = CHECKPOINTS
    checkpoints.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            sys.executable,
            str(Path(__file__).with_name("diagnostics.py")),
            "--monitor",
            str(checkpoints / "runtime-metrics.jsonl"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    snapshot = snapshot_download(
        repo_id=model,
        revision=revision,
        allow_patterns=[
            "*.json",
            "*.safetensors",
            "*.txt",
            "*.model",
            "*.jinja",
        ],
    )
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.is_symlink():
        MODEL_PATH.unlink()
    elif MODEL_PATH.exists():
        raise ValueError("/models/base already exists and is not a symlink")
    MODEL_PATH.symlink_to(snapshot, target_is_directory=True)
    config = json.loads(
        Path(__file__).with_name("backend_config.json").read_text()
    )
    identity = {
        "model_name": model,
        "model_revision": revision,
        "model_path": str(MODEL_PATH),
        "snapshot_path": snapshot,
        "skyrl_commit": os.environ["SKYRL_COMMIT"],
        "backend_config": config,
        "source_sha256": {
            name: hashlib.sha256(
                Path(__file__).with_name(name).read_bytes()
            ).hexdigest()
            for name in (
                "entrypoint.py",
                "backend_config.json",
                "diagnostics.py",
            )
        },
    }
    (checkpoints / "server-identity.json").write_text(
        json.dumps(identity, indent=2) + "\n"
    )
    print(json.dumps({"training_server_identity": identity}), flush=True)
    # SkyRL reads its uv parent command to launch the background training engine.
    args = [
        "uv",
        "run",
        "--frozen",
        "--no-sync",
        "--extra",
        "fsdp",
        "--extra",
        "tinker",
        "-m",
        "skyrl.tinker.api",
        "--base-model",
        str(MODEL_PATH),
        "--backend",
        "fsdp",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--checkpoints-base",
        str(checkpoints),
        "--database-url",
        "sqlite:////checkpoints/tinker.db",
        "--backend-config",
        json.dumps(config),
    ]
    os.execvp("uv", args)


if __name__ == "__main__":
    main()
