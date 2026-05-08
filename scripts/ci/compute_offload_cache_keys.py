"""Compute cache keys for offloaded CI lanes."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

SUPPORTED_LANES = {"default", "modal-server-mysql"}
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class OffloadCacheKeys:
    """Cache key family used by the offload workflow."""

    uv_key: str
    uv_restore_prefix: str
    legacy_uv_restore_prefix: str
    image_key: str
    image_restore_prefix: str
    legacy_image_restore_prefix: str
    junit_restore_key: str
    junit_restore_prefix: str
    legacy_junit_restore_prefix: str
    junit_save_key: str


def _read_file(path: Path) -> bytes:
    return path.read_bytes() if path.exists() else b""


def _hash_parts(parts: list[tuple[str, str | bytes]]) -> str:
    digest = hashlib.sha256()
    for name, value in parts:
        digest.update(name.encode())
        digest.update(b"\0")
        if isinstance(value, str):
            value = value.encode()
        digest.update(value)
        digest.update(b"\0")
    return digest.hexdigest()


def _load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _config_for_lane(lane: str) -> str:
    if lane == "default":
        return "offload.toml"
    if lane == "modal-server-mysql":
        return "offload-modal-server-mysql.toml"
    raise ValueError(
        f"Unsupported offload lane '{lane}'. Expected one of: "
        f"{', '.join(sorted(SUPPORTED_LANES))}."
    )


def _uv_fingerprint(root: Path) -> str:
    return _hash_parts(
        [
            ("pyproject.toml", _read_file(root / "pyproject.toml")),
            (
                "scripts/ci/modal_sandbox_requirements.txt",
                _read_file(root / "scripts/ci/modal_sandbox_requirements.txt"),
            ),
        ]
    )


def _image_fingerprint(root: Path) -> str:
    default_config = _load_toml(root / "offload.toml")
    mysql_config = _load_toml(root / "offload-modal-server-mysql.toml")
    parts: list[tuple[str, str | bytes]] = [
        ("Dockerfile.ci", _read_file(root / "Dockerfile.ci")),
        (
            "Dockerfile.ci.dockerignore",
            _read_file(root / "Dockerfile.ci.dockerignore"),
        ),
        ("pyproject.toml", _read_file(root / "pyproject.toml")),
        (
            "scripts/ci/export_offload_integration_requirements.py",
            _read_file(
                root / "scripts/ci/export_offload_integration_requirements.py"
            ),
        ),
        (
            "src/zenml/cli/integration.py",
            _read_file(root / "src/zenml/cli/integration.py"),
        ),
        (
            "src/zenml/integrations/integration.py",
            _read_file(root / "src/zenml/integrations/integration.py"),
        ),
        (
            "src/zenml/integrations/registry.py",
            _read_file(root / "src/zenml/integrations/registry.py"),
        ),
        (
            "offload.toml:provider.prepare_command",
            default_config["provider"]["prepare_command"],
        ),
        (
            "offload-modal-server-mysql.toml:provider.prepare_command",
            mysql_config["provider"]["prepare_command"],
        ),
        (
            "offload.toml:offload.sandbox_project_root",
            default_config["offload"]["sandbox_project_root"],
        ),
        (
            "offload-modal-server-mysql.toml:offload.sandbox_project_root",
            mysql_config["offload"]["sandbox_project_root"],
        ),
    ]
    for path in sorted(
        (root / "src/zenml/integrations").glob("*/__init__.py")
    ):
        parts.append((str(path.relative_to(root)), _read_file(path)))
    return _hash_parts(parts)


def _junit_fingerprint(root: Path, lane: str) -> str:
    config_name = _config_for_lane(lane)
    config = _load_toml(root / config_name)
    parts: list[tuple[str, str | bytes]] = [
        ("config_filename", config_name),
        ("framework.command", config["framework"]["command"]),
        ("framework.run_args", config["framework"]["run_args"]),
    ]
    for group_name in sorted(config["groups"]):
        parts.append(
            (
                f"groups.{group_name}.filters",
                config["groups"][group_name]["filters"],
            )
        )
    return _hash_parts(parts)


def compute_offload_cache_keys(
    *,
    lane: str,
    runner_os: str,
    python_version: str,
    run_id: str,
    run_attempt: str,
    root: Path = ROOT,
) -> OffloadCacheKeys:
    """Compute deterministic offload cache keys."""
    if lane not in SUPPORTED_LANES:
        _config_for_lane(lane)

    uv_fingerprint = _uv_fingerprint(root)
    image_fingerprint = _image_fingerprint(root)
    junit_fingerprint = _junit_fingerprint(root, lane)

    uv_prefix = f"offload-uv-v1-{runner_os}-py{python_version}-"
    image_prefix = f"offload-image-v2-{runner_os}-"
    junit_prefix = f"offload-junit-v2-{lane}-{junit_fingerprint}-"

    return OffloadCacheKeys(
        uv_key=f"{uv_prefix}{uv_fingerprint}",
        uv_restore_prefix=uv_prefix,
        legacy_uv_restore_prefix=f"uv-{runner_os}-{python_version}-",
        image_key=f"{image_prefix}{image_fingerprint}",
        image_restore_prefix=image_prefix,
        legacy_image_restore_prefix=f"offload-image-v1-{runner_os}-{python_version}-",
        junit_restore_key=junit_prefix,
        junit_restore_prefix=junit_prefix,
        legacy_junit_restore_prefix=f"offload-junit-{lane}-{runner_os}-",
        junit_save_key=f"{junit_prefix}{run_id}-{run_attempt}",
    )


def _write_github_outputs(keys: OffloadCacheKeys) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as output_file:
        for field_name, value in keys.__dict__.items():
            output_file.write(f"{field_name}={value}\n")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--runner-os", required=True)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)
    try:
        keys = compute_offload_cache_keys(
            lane=args.lane,
            runner_os=args.runner_os,
            python_version=args.python_version,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print("Computed offload cache keys:")
    print(f"  uv_key={keys.uv_key}")
    print(f"  image_key={keys.image_key}")
    print(f"  junit_restore_prefix={keys.junit_restore_prefix}")
    print(f"  junit_save_key={keys.junit_save_key}")
    _write_github_outputs(keys)
    return 0


if __name__ == "__main__":
    sys.exit(main())
