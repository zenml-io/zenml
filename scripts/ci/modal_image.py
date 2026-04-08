"""Build and cache Modal images for fast CI."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / ".modal-cache" / "image-manifest.json"
DEFAULT_REQUIREMENTS_DIR = REPO_ROOT / ".modal-cache" / "requirements"
DEFAULT_MODAL_APP_NAME = "zenml-fast-ci"
DEFAULT_SANDBOX_CPU = 4.0
DEFAULT_SANDBOX_MEMORY_MB = 8192
DEFAULT_TARGET_OS = "Linux"
DEFAULT_MODAL_TARGET_PLATFORM = "x86_64-manylinux_2_35"
DEPENDENCY_IMAGE_BUILD_VERSION = "v2"
COLLECTION_FINGERPRINT_SHARED_PATHS = (
    "pyproject.toml",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/venv_clone_utils.py",
    "tests/harness",
)
SUITE_COLLECTION_FINGERPRINT_PATHS = {
    "unit": ("tests/unit",),
    "integration": ("tests/integration",),
}


@dataclass(frozen=True)
class CachedImageManifest:
    """Locally cached metadata for a dependency image."""

    fingerprint: str
    image_id: str
    python_version: str


@dataclass(frozen=True)
class ResolvedDependencyImage:
    """A dependency image plus cache metadata."""

    image: Any
    fingerprint: str
    cache_hit: bool


def collection_fingerprint_paths_for_suite(suite_name: str) -> tuple[str, ...]:
    """Return the files that affect pytest node discovery for one suite."""
    suite_paths = SUITE_COLLECTION_FINGERPRINT_PATHS.get(suite_name)
    if suite_paths is None:
        raise ValueError(
            f"Unsupported suite for collection fingerprint: {suite_name}"
        )
    return COLLECTION_FINGERPRINT_SHARED_PATHS + suite_paths


def _log(message: str) -> None:
    """Print a timestamped image-build log line."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [modal-image] {message}", flush=True)


def compute_dependency_fingerprint(
    *,
    python_version: str,
    requirements_path: Path,
) -> str:
    """Compute a stable dependency fingerprint for the Modal image."""
    digest = hashlib.sha256()
    digest.update(
        f"builder_version={DEPENDENCY_IMAGE_BUILD_VERSION}\n".encode()
    )
    digest.update(f"python={python_version}\n".encode())
    digest.update(b"resolved_requirements\n")
    digest.update(requirements_path.read_bytes())
    digest.update(b"\n")

    return digest.hexdigest()


def compute_collection_fingerprint(
    *,
    python_version: str,
    test_environment: str,
    suite_name: str,
    pytest_import_mode: Optional[str],
    root: Path = REPO_ROOT,
) -> str:
    """Compute a cache key for suite node collection."""
    digest = hashlib.sha256()
    digest.update(f"python={python_version}\n".encode())
    digest.update(f"test_environment={test_environment}\n".encode())
    digest.update(f"suite_name={suite_name}\n".encode())
    digest.update(
        f"pytest_import_mode={pytest_import_mode or 'default'}\n".encode()
    )

    for relative_path in collection_fingerprint_paths_for_suite(suite_name):
        _update_digest_for_relative_path(
            digest=digest,
            root=root,
            relative_path=relative_path,
        )

    return digest.hexdigest()


FINGERPRINT_IGNORED_SUFFIXES = (".pyc", ".pyo")
FINGERPRINT_IGNORED_DIRS = {
    "__pycache__",
    ".egg-info",
    ".git",
    ".hypothesis",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def _should_skip_for_fingerprint(path: Path) -> bool:
    """Return True if a path should be excluded from fingerprint computation."""
    if path.suffix in FINGERPRINT_IGNORED_SUFFIXES:
        return True
    return any(part in FINGERPRINT_IGNORED_DIRS for part in path.parts)


def _update_digest_for_relative_path(
    *,
    digest: Any,
    root: Path,
    relative_path: str,
) -> None:
    """Update a digest with one file or directory tree."""
    path = root / relative_path
    if path.is_dir():
        for child in sorted(
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file()
            and not _should_skip_for_fingerprint(candidate.relative_to(root))
        ):
            digest.update(str(child.relative_to(root)).encode())
            digest.update(b"\n")
            digest.update(child.read_bytes())
            digest.update(b"\n")
        return

    digest.update(relative_path.encode())
    digest.update(b"\n")
    digest.update(path.read_bytes())
    digest.update(b"\n")


def _load_manifest_data(manifest_path: Path) -> dict[str, Any]:
    """Load the cache manifest and normalize legacy layouts."""
    if not manifest_path.exists():
        return {"dependency_images": {}, "execution_images": {}}

    data = json.loads(manifest_path.read_text())
    if "dependency_images" in data or "execution_images" in data:
        return {
            "dependency_images": dict(data.get("dependency_images", {})),
            "execution_images": dict(data.get("execution_images", {})),
        }

    if {"fingerprint", "image_id", "python_version"} <= set(data):
        return {
            "dependency_images": {
                data["fingerprint"]: {
                    "fingerprint": data["fingerprint"],
                    "image_id": data["image_id"],
                    "python_version": data["python_version"],
                }
            },
            "execution_images": {},
        }

    return {"dependency_images": {}, "execution_images": {}}


def load_cached_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> Optional[CachedImageManifest]:
    """Load the cached dependency image entry that matches the manifest."""
    data = _load_manifest_data(manifest_path)
    dependency_images = data["dependency_images"]
    if len(dependency_images) == 1:
        manifest_data = next(iter(dependency_images.values()))
        return CachedImageManifest(**manifest_data)
    return None


def load_cached_dependency_manifest(
    *,
    fingerprint: str,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> Optional[CachedImageManifest]:
    """Load one cached dependency image entry by fingerprint."""
    data = _load_manifest_data(manifest_path)
    manifest_data = data["dependency_images"].get(fingerprint)
    if manifest_data is None:
        return None
    return CachedImageManifest(**manifest_data)


def save_cached_manifest(
    manifest: CachedImageManifest,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> None:
    """Persist one dependency image entry in the shared cache manifest."""
    data = _load_manifest_data(manifest_path)
    data["dependency_images"][manifest.fingerprint] = asdict(manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True))


def _build_dependency_image(
    modal: Any,
    python_version: str,
    requirements_path: Path,
) -> Any:
    """Build a dependency image with only third-party dependencies installed.

    Source code is fetched separately via a git snapshot volume, which keeps
    source edits from invalidating the expensive dependency layer.
    """
    _log(f"Preparing dependency image definition for Python {python_version}.")
    image = (
        modal.Image.debian_slim(python_version=python_version)
        .apt_install("git", "graphviz")
        .workdir("/app")
        .add_local_file(
            str(requirements_path),
            "/tmp/modal-fast-ci-requirements.txt",
            copy=True,
        )
        .run_commands(
            "python -m pip install --upgrade wheel pip uv",
            "uv pip install --system -r /tmp/modal-fast-ci-requirements.txt",
            "uv pip uninstall --system multipart || true",
            "uv pip install --system 'setuptools<82'",
            "python -m compileall /usr/local/lib/python*/site-packages/zenml "
            "/usr/local/lib/python*/site-packages/sqlmodel "
            "/usr/local/lib/python*/site-packages/pydantic "
            "-q -j 0 2>/dev/null || true",
        )
    )
    _log("Dependency image definition prepared (Modal layer cache applies).")
    return image


def compute_requirements_export_fingerprint(
    *,
    python_version: str,
    target_os: str,
    target_platform: str,
    root: Path = REPO_ROOT,
) -> str:
    """Compute the cache key for the resolved requirements export."""
    digest = hashlib.sha256()
    digest.update(f"python={python_version}\n".encode())
    digest.update(f"target_os={target_os}\n".encode())
    digest.update(f"target_platform={target_platform}\n".encode())

    for relative_path in (
        "pyproject.toml",
        "scripts/install-zenml-dev.sh",
        "scripts/install_dev_requirements.py",
        "src/zenml/integrations",
    ):
        _update_digest_for_relative_path(
            digest=digest,
            root=root,
            relative_path=relative_path,
        )

    return digest.hexdigest()


def export_dependency_requirements(
    *,
    python_version: str,
    target_os: str = DEFAULT_TARGET_OS,
    target_platform: str = DEFAULT_MODAL_TARGET_PLATFORM,
    output_path: Optional[Path] = None,
    root: Path = REPO_ROOT,
) -> Path:
    """Export the dependency set using the dev install script workflow."""
    platform_suffix = target_platform.lower().replace("/", "-")
    requirements_path = output_path or (
        DEFAULT_REQUIREMENTS_DIR
        / (
            "fast-ci-requirements-"
            f"{python_version}-{target_os.lower()}-{platform_suffix}.txt"
        )
    )
    requirements_path.parent.mkdir(parents=True, exist_ok=True)
    fingerprint_path = requirements_path.with_suffix(
        requirements_path.suffix + ".fingerprint"
    )
    fingerprint = compute_requirements_export_fingerprint(
        python_version=python_version,
        target_os=target_os,
        target_platform=target_platform,
        root=root,
    )

    if (
        requirements_path.exists()
        and fingerprint_path.exists()
        and fingerprint_path.read_text(encoding="utf-8").strip() == fingerprint
    ):
        _log(f"Using cached resolved requirements at {requirements_path}.")
        return requirements_path

    _log("Exporting resolved requirements for the dependency image.")
    started_at = time.time()
    command = [
        "/bin/sh",
        str(root / "scripts" / "install-zenml-dev.sh"),
        "--integrations",
        "yes",
        "--export-requirements-file",
        str(requirements_path),
        "--target-python-version",
        python_version,
        "--target-os",
        target_os,
        "--target-platform",
        target_platform,
    ]
    result = subprocess.run(
        command,
        check=False,
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, end="", flush=True)
        if result.stderr:
            print(result.stderr, end="", flush=True)
        raise subprocess.CalledProcessError(
            result.returncode,
            command,
            output=result.stdout,
            stderr=result.stderr,
        )
    fingerprint_path.write_text(fingerprint, encoding="utf-8")
    _log(f"Resolved requirements exported in {time.time() - started_at:.1f}s.")
    return requirements_path


def resolve_dependency_image(
    *,
    python_version: str,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> Any:
    """Resolve a dependency image using Modal's server-side layer cache."""
    import modal

    _log("Resolving dependency image.")
    requirements_path = export_dependency_requirements(
        python_version=python_version,
        target_os=DEFAULT_TARGET_OS,
        target_platform=DEFAULT_MODAL_TARGET_PLATFORM,
    )
    fingerprint = compute_dependency_fingerprint(
        python_version=python_version,
        requirements_path=requirements_path,
    )
    cached_manifest = load_cached_dependency_manifest(
        fingerprint=fingerprint,
        manifest_path=manifest_path,
    )
    if cached_manifest is not None:
        try:
            image = modal.Image.from_id(cached_manifest.image_id)
            _log("Using cached dependency image from the local manifest.")
            return ResolvedDependencyImage(
                image=image,
                fingerprint=fingerprint,
                cache_hit=True,
            )
        except Exception:
            cached_manifest = None

    image = _build_dependency_image(modal, python_version, requirements_path)
    return ResolvedDependencyImage(
        image=image,
        fingerprint=fingerprint,
        cache_hit=False,
    )
