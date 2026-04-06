"""Build and cache Modal images for fast CI."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / ".modal-cache" / "image-manifest.json"
DEFAULT_MODAL_APP_NAME = "zenml-fast-ci"
DEFAULT_SANDBOX_CPU = 4.0
DEFAULT_SANDBOX_MEMORY_MB = 8192
DEPENDENCY_FINGERPRINT_PATHS = (
    "pyproject.toml",
    "README.md",
    "zen-test",
    "scripts/install-zenml-dev.sh",
)
EXECUTION_FINGERPRINT_PATHS = (
    "zen-test",
    "scripts",
    "tests",
)
SHARED_EXECUTION_OVERLAY_PATHS = (
    "zen-test",
    "scripts",
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/venv_clone_utils.py",
    "tests/harness",
)
SUITE_EXECUTION_OVERLAY_PATHS = {
    "unit": ("tests/unit",),
    "integration": ("tests/integration", "examples"),
}


@dataclass(frozen=True)
class CachedImageManifest:
    """Locally cached metadata for a dependency image."""

    fingerprint: str
    image_id: str
    python_version: str


@dataclass(frozen=True)
class CachedExecutionImageManifest:
    """Locally cached metadata for a prepared execution image."""

    fingerprint: str
    image_id: str
    python_version: str
    test_environment: str
    dependency_fingerprint: str
    suite_name: str = ""


@dataclass(frozen=True)
class ResolvedDependencyImage:
    """A dependency image plus cache metadata."""

    image: Any
    fingerprint: str
    cache_hit: bool


def execution_overlay_paths_for_suite(suite_name: Optional[str]) -> tuple[str, ...]:
    """Return the synced overlay paths for a suite-specific execution image."""
    if not suite_name:
        return EXECUTION_FINGERPRINT_PATHS

    suite_paths = SUITE_EXECUTION_OVERLAY_PATHS.get(suite_name)
    if suite_paths is None:
        raise ValueError(f"Unsupported suite for execution overlay: {suite_name}")
    return SHARED_EXECUTION_OVERLAY_PATHS + suite_paths


def execution_overlay_paths_combined() -> tuple[str, ...]:
    """Return overlay paths covering all suites in a single image."""
    all_suite_paths: list[str] = []
    for suite_paths in SUITE_EXECUTION_OVERLAY_PATHS.values():
        all_suite_paths.extend(suite_paths)
    return SHARED_EXECUTION_OVERLAY_PATHS + tuple(all_suite_paths)


def _log(message: str) -> None:
    """Print a timestamped image-build log line."""
    from datetime import datetime

    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [modal-image] {message}", flush=True)


def compute_dependency_fingerprint(
    *,
    python_version: str,
    install_integrations: bool = True,
    root: Path = REPO_ROOT,
) -> str:
    """Compute a stable dependency fingerprint for the Modal image."""
    digest = hashlib.sha256()
    digest.update(f"python={python_version}\n".encode())
    digest.update(
        f"install_integrations={'yes' if install_integrations else 'no'}\n".encode()
    )

    for relative_path in DEPENDENCY_FINGERPRINT_PATHS:
        path = root / relative_path
        digest.update(f"{relative_path}\n".encode())
        digest.update(path.read_bytes())
        digest.update(b"\n")

    return digest.hexdigest()


def compute_execution_fingerprint(
    *,
    python_version: str,
    test_environment: str,
    dependency_fingerprint: str,
    suite_name: Optional[str] = None,
    overlay_paths: Optional[Sequence[str]] = None,
    root: Path = REPO_ROOT,
) -> str:
    """Compute a stable fingerprint for the prepared execution snapshot."""
    digest = hashlib.sha256()
    digest.update(f"python={python_version}\n".encode())
    digest.update(f"test_environment={test_environment}\n".encode())
    digest.update(f"dependency_fingerprint={dependency_fingerprint}\n".encode())
    digest.update(f"suite_name={suite_name or 'all'}\n".encode())

    for relative_path in overlay_paths or execution_overlay_paths_for_suite(
        suite_name
    ):
        _update_digest_for_relative_path(
            digest=digest,
            root=root,
            relative_path=relative_path,
        )

    return digest.hexdigest()


FINGERPRINT_IGNORED_SUFFIXES = (".pyc", ".pyo")
FINGERPRINT_IGNORED_DIRS = {"__pycache__", ".egg-info", ".git"}


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


def load_cached_execution_manifest(
    *,
    fingerprint: str,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> Optional[CachedExecutionImageManifest]:
    """Load one cached execution image entry by fingerprint."""
    data = _load_manifest_data(manifest_path)
    manifest_data = data["execution_images"].get(fingerprint)
    if manifest_data is None:
        return None
    return CachedExecutionImageManifest(**manifest_data)


def save_cached_manifest(
    manifest: CachedImageManifest,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> None:
    """Persist one dependency image entry in the shared cache manifest."""
    data = _load_manifest_data(manifest_path)
    data["dependency_images"][manifest.fingerprint] = asdict(manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True))


def save_cached_execution_manifest(
    manifest: CachedExecutionImageManifest,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> None:
    """Persist one execution image entry in the shared cache manifest."""
    data = _load_manifest_data(manifest_path)
    data["execution_images"][manifest.fingerprint] = asdict(manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True))


def _build_dependency_image(modal: Any, python_version: str) -> Any:
    """Build a dependency image with Modal's server-side layer caching.

    Uses copy=True and run_commands so Modal hashes the layer by file
    content. If pyproject.toml / install script haven't changed, Modal
    returns the cached layer instantly — even across machines and CI runs.
    """
    _log(f"Building dependency image for Python {python_version}.")
    image = (
        modal.Image.debian_slim(python_version=python_version)
        .apt_install("git", "graphviz")
        .workdir("/app")
        .add_local_file(
            str(REPO_ROOT / "pyproject.toml"),
            "/app/pyproject.toml",
            copy=True,
        )
        .add_local_file(
            str(REPO_ROOT / "README.md"),
            "/app/README.md",
            copy=True,
        )
        .add_local_file(
            str(REPO_ROOT / "zen-test"),
            "/app/zen-test",
            copy=True,
        )
        .add_local_file(
            str(REPO_ROOT / "scripts" / "install-zenml-dev.sh"),
            "/app/scripts/install-zenml-dev.sh",
            copy=True,
        )
        .add_local_dir(
            str(REPO_ROOT / "src"),
            "/app/src",
            copy=True,
        )
        .run_commands(
            "cd /app && chmod +x /app/zen-test /app/scripts/install-zenml-dev.sh "
            "&& bash /app/scripts/install-zenml-dev.sh --system "
            "--integrations yes "
            "&& uv pip install --system 'setuptools<82'",
        )
    )
    _log("Dependency image built (Modal layer cache applies).")
    return image


def resolve_dependency_image(
    *,
    python_version: str,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> Any:
    """Resolve a dependency image using Modal's server-side layer cache."""
    import modal

    _log("Resolving dependency image.")
    fingerprint = compute_dependency_fingerprint(
        python_version=python_version,
        install_integrations=True,
    )
    image = _build_dependency_image(modal, python_version)
    return ResolvedDependencyImage(
        image=image,
        fingerprint=fingerprint,
        cache_hit=True,
    )
