"""Run Linux fast CI on Modal and locally from the same entrypoint."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ci.modal_image import (
    DEFAULT_MODAL_APP_NAME,
    DEFAULT_SANDBOX_CPU,
    DEFAULT_SANDBOX_MEMORY_MB,
    CachedImageManifest,
    ResolvedDependencyImage,
    compute_collection_fingerprint,
    resolve_dependency_image,
    save_cached_manifest,
)
from scripts.ci.scheduler import (
    DEFAULT_INTEGRATION_TEST_DURATION_SECONDS,
    DEFAULT_UNIT_TEST_DURATION_SECONDS,
    ScheduledBatch,
    read_durations_file,
    schedule_batches,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS_DIR = REPO_ROOT / "test-results" / "modal-fast-ci"
DEFAULT_DURATION_CACHE_PATH = (
    REPO_ROOT / ".modal-cache" / "test_durations.json"
)
DEFAULT_NODE_ID_CACHE_DIR = REPO_ROOT / ".modal-cache" / "node-ids"
RUNNER_EXIT_TEST_FAILURE = 1
RUNNER_EXIT_INFRA_FAILURE = 2
DEFAULT_REPO_VOLUME_NAME = "zenml-fast-ci-source-cache"
REMOTE_VOLUME_ROOT = "/mnt/zenml-fast-ci"
REMOTE_REPO_CACHE_ROOT = f"{REMOTE_VOLUME_ROOT}/repo-cache"
REMOTE_REPO_SNAPSHOTS_ROOT = f"{REMOTE_VOLUME_ROOT}/repo-snapshots"
GIT_SOURCE_CACHE_VERSION = "v3"
REMOTE_RUNTIME_ROOT = "/tmp/zenml-fast-ci"
REMOTE_ARTIFACTS_DIR = f"{REMOTE_RUNTIME_ROOT}/artifacts"
REMOTE_CONFIG_DIR = f"{REMOTE_RUNTIME_ROOT}/config"
REMOTE_LOCAL_STORES_DIR = f"{REMOTE_RUNTIME_ROOT}/local-stores"
REMOTE_LOCAL_REPOSITORY_DIR = f"{REMOTE_RUNTIME_ROOT}/repo"
NODE_ID_PATH = "/tmp/zenml-batch-node-ids.txt"
JUNIT_PATH = f"{REMOTE_ARTIFACTS_DIR}/junit.xml"
RUN_LOG_PATH = f"{REMOTE_ARTIFACTS_DIR}/batch.log"
REMOTE_COVERAGE_PATH = f"{REMOTE_ARTIFACTS_DIR}/.coverage"
COVERAGE_FILE_ENV = "COVERAGE_FILE"
JUNIT_LOG_START = "__MODAL_JUNIT_START__"
JUNIT_LOG_END = "__MODAL_JUNIT_END__"
INTEGRATION_QUEUE_DEPTH_MULTIPLIER = 3
UNIT_QUEUE_DEPTH_MULTIPLIER = 1
BATCH_MANIFESTS_DIRNAME = "batches"
BATCH_NODE_UPLOAD_TIMEOUT_SECONDS = 120
MODAL_ENV_PAYLOAD_MAX_BYTES = 28000  # Modal caps secret values at 32768 bytes
INTEGRATION_SCOPE_CHUNK_SIZE = 16
SPARSE_CHECKOUT_PATHS = (
    "src",
    "tests",
    "scripts",
    "examples",
    "templates",
    "pyproject.toml",
    "alembic.ini",
    "README.md",
    "zen-test",
)

RUNNER_COMMAND = """\
test_environment="${ZENML_TEST_ENVIRONMENT}"
artifacts_dir="${ZENML_ARTIFACTS_DIR}"
batch_name="${ZENML_BATCH_NAME:-batch}"
source_repo_root="${ZENML_BATCH_REPOSITORY_PATH}"
repo_root="${ZENML_LOCAL_REPOSITORY_PATH}"

rm -rf "$repo_root"
mkdir -p "$repo_root"
tar -C "$source_repo_root" -cf - . | tar -C "$repo_root" -xf -

cd "$repo_root"
export PYTHONUNBUFFERED=1
mkdir -p \
  "${artifacts_dir}" \
  "${ZENML_CONFIG_PATH}" \
  "${ZENML_LOCAL_STORES_PATH}"

if [[ -n "${ZENML_NODE_IDS_B64:-}" ]]; then
  echo "$ZENML_NODE_IDS_B64" | base64 -d > "${ZENML_NODE_ID_PATH}"
else
  for _ in $(seq 1 600); do
    if [[ -s "${ZENML_NODE_ID_PATH}" ]]; then
      break
    fi
    sleep 0.2
  done
fi

if [[ ! -s "${ZENML_NODE_ID_PATH}" ]]; then
  echo "Batch node ID file was not uploaded to ${ZENML_NODE_ID_PATH}" >&2
  exit 97
fi

mapfile -t NODE_IDS < "${ZENML_NODE_ID_PATH}"

pytest_args=(
  --color=yes
  -ra
  -q
  --environment "$test_environment"
  --no-provision
  -p no:randomly
  -p no:rerunfailures
  --junitxml="${ZENML_JUNIT_PATH}"
)

if [[ "${ZENML_COLLECT_COVERAGE:-1}" == "1" ]]; then
  pytest_args+=(
    --cov=src/zenml
    --cov-config=pyproject.toml
    --cov-report=
  )
fi

if [[ "${ZENML_PYTEST_WORKERS:-0}" -gt 1 ]]; then
  pytest_args+=(
    -n "${ZENML_PYTEST_WORKERS}"
    --dist "${ZENML_PYTEST_DIST:-worksteal}"
  )
fi

if [[ -n "${ZENML_PYTEST_IMPORT_MODE:-}" ]]; then
  pytest_args+=(
    --import-mode "${ZENML_PYTEST_IMPORT_MODE}"
  )
fi

pytest_args+=("${NODE_IDS[@]}")
pytest_exit=0
python -m pytest "${pytest_args[@]}" &
pytest_pid=$!

while kill -0 "$pytest_pid" >/dev/null 2>&1; do
  printf '[heartbeat] %s pytest still running for %s\n' "$(date '+%H:%M:%S')" "$batch_name"
  sleep 15
done &
heartbeat_pid=$!

wait "$pytest_pid" || pytest_exit=$?
kill "$heartbeat_pid" >/dev/null 2>&1 || true
wait "$heartbeat_pid" 2>/dev/null || true

if [[ -f "${ZENML_JUNIT_PATH}" ]]; then
  echo "${ZENML_JUNIT_START}"
  python -c 'import base64, pathlib, sys; print(base64.b64encode(pathlib.Path(sys.argv[1]).read_bytes()).decode("ascii"))' "${ZENML_JUNIT_PATH}"
  echo "${ZENML_JUNIT_END}"
fi
exit "$pytest_exit"
"""


@dataclass
class SuiteConfig:
    """Configuration for a single suite run."""

    name: str
    test_environment: str
    default_duration: float
    batch_timeout: int
    pytest_workers: int = 0
    pytest_dist: str = "worksteal"
    pytest_import_mode: Optional[str] = None
    collect_coverage: bool = True


@dataclass
class BatchResult:
    """Result for one Modal test batch."""

    suite: str
    batch_name: str
    node_ids: List[str]
    expected_duration: float
    runtime_seconds: float
    exit_code: int
    junit_xml: str
    failed_node_ids: List[str]
    log_output: str
    coverage_path: Optional[Path]


@dataclass(frozen=True)
class FailureDetail:
    """Structured information for one failed testcase."""

    batch_name: str
    node_id: str
    kind: str
    summary: str
    details: str


@dataclass
class BatchExecution:
    """Running Modal batch state."""

    suite: SuiteConfig
    batch_name: str
    scheduled_batch: ScheduledBatch
    sandbox: Any
    artifacts_dir: Path
    start_time: float


@dataclass
class RunnerSummary:
    """Top-level runner result."""

    results: List[BatchResult]
    startup_summary: Optional["StartupSummary"] = None


@dataclass(frozen=True)
class SuiteCollection:
    """Collected suite metadata used for scheduling and execution."""

    suite: SuiteConfig
    node_ids: List[str]
    estimated_total_duration: float
    node_id_cache_hit: bool


@dataclass(frozen=True)
class GitSourceRef:
    """Immutable git source reference used to prepare remote snapshots."""

    commit_sha: str
    remote_url: str
    cache_namespace: str


@dataclass(frozen=True)
class PreparedGitSourceSnapshot:
    """Resolved git snapshot state shared by all sandboxes in a run."""

    volume: Any
    snapshot_path: str
    cache_hit: bool
    commit_sha: str


@dataclass(frozen=True)
class StartupSummary:
    """Warm-start and launch metadata for one runner invocation."""

    dependency_cache_hit: bool
    source_snapshot_cache_hit: bool
    node_id_cache_hits: dict[str, bool]
    launch_to_first_batch_seconds: float


@dataclass
class SuiteRunOutcome:
    """One suite execution outcome plus launch timing."""

    results: List[BatchResult]
    first_launch_started_at: Optional[float]


class InfraFailure(RuntimeError):
    """Raised when Modal infrastructure fails."""


def log(message: str) -> None:
    """Print a timestamped runner log line."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [modal-runner] {message}", flush=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse CLI args for CI and local runs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        action="append",
        choices=("unit", "integration"),
        required=True,
        help="Suite to run. May be passed multiple times.",
    )
    parser.add_argument(
        "--test-environment",
        default="default",
        help="ZenML test environment to provision and run against.",
    )
    parser.add_argument(
        "--python-version",
        default="3.13",
        help="Python version for the Modal image.",
    )
    parser.add_argument(
        "--max-sandboxes",
        type=int,
        default=20,
        help="Maximum number of parallel sandboxes per suite.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="Directory where JUnit, coverage, and summary artifacts are written.",
    )
    parser.add_argument(
        "--local-run-name",
        default="local",
        help="Run label for local execution.",
    )
    parser.add_argument(
        "--use-existing-test-durations",
        action="store_true",
        default=True,
        help="Use the repository .test_durations file if present.",
    )
    parser.add_argument(
        "--unit-batch-timeout",
        type=int,
        default=900,
        help="Sandbox timeout in seconds for unit batches.",
    )
    parser.add_argument(
        "--integration-batch-timeout",
        type=int,
        default=960,
        help="Sandbox timeout in seconds for integration batches.",
    )
    parser.add_argument(
        "--sandbox-cpu",
        type=float,
        default=DEFAULT_SANDBOX_CPU,
        help="vCPUs to allocate to each Modal sandbox.",
    )
    parser.add_argument(
        "--sandbox-memory-mb",
        type=int,
        default=DEFAULT_SANDBOX_MEMORY_MB,
        help="Memory in MB to allocate to each Modal sandbox.",
    )
    parser.add_argument(
        "--unit-pytest-workers",
        type=int,
        default=None,
        help=(
            "Number of in-shard pytest-xdist workers for unit batches. "
            "Defaults to the sandbox CPU count."
        ),
    )
    parser.add_argument(
        "--unit-pytest-dist",
        choices=("worksteal", "load", "loadscope"),
        default="worksteal",
        help=(
            "pytest-xdist distribution mode for unit batches. "
            "Use worksteal or load for balanced shards; reserve loadscope "
            "for tests that must stay grouped by scope."
        ),
    )
    parser.add_argument(
        "--unit-max-sandboxes",
        type=int,
        default=None,
        help=(
            "Maximum number of outer sandboxes reserved for the unit suite when "
            "running multiple suites. Defaults to 3 for unit+integration runs."
        ),
    )
    parser.add_argument(
        "--collect-coverage",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Collect coverage data for test shards.",
    )
    return parser.parse_args(argv)


def suite_configs_from_args(args: argparse.Namespace) -> List[SuiteConfig]:
    """Convert parsed args into suite configs."""
    configs: List[SuiteConfig] = []
    for suite in args.suite:
        batch_timeout = (
            args.unit_batch_timeout
            if suite == "unit"
            else args.integration_batch_timeout
        )
        pytest_workers = (
            _default_unit_pytest_workers(
                configured_workers=args.unit_pytest_workers,
                sandbox_cpu=args.sandbox_cpu,
            )
            if suite == "unit"
            else 0
        )
        configs.append(
            SuiteConfig(
                name=suite,
                test_environment=args.test_environment,
                default_duration=_default_duration_for_suite(suite),
                batch_timeout=batch_timeout,
                pytest_workers=pytest_workers,
                pytest_dist=(
                    args.unit_pytest_dist if suite == "unit" else "worksteal"
                ),
                pytest_import_mode="importlib",
                collect_coverage=args.collect_coverage,
            )
        )
    return configs


def _default_duration_for_suite(suite: str) -> float:
    """Return the fallback duration for one suite."""
    if suite == "unit":
        return DEFAULT_UNIT_TEST_DURATION_SECONDS
    return DEFAULT_INTEGRATION_TEST_DURATION_SECONDS


def _default_unit_pytest_workers(
    *,
    configured_workers: Optional[int],
    sandbox_cpu: float,
) -> int:
    """Choose a conservative default xdist worker count for unit shards."""
    if configured_workers is not None:
        return max(0, configured_workers)
    return max(1, min(4, int(sandbox_cpu)))


def _retry_modal_call(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Retry transient Modal API calls a few times before failing."""
    last_error: Optional[Exception] = None
    for attempt in range(3):
        try:
            return func(*args, **kwargs)
        except Exception as error:  # pragma: no cover - exercised via mocks
            last_error = error
            if attempt == 2:
                break
            log(
                f"Retrying Modal API call {func.__name__} after error: {error} "
                f"(attempt {attempt + 2}/3)."
            )
            time.sleep(2**attempt)
    raise InfraFailure(str(last_error)) from last_error


def _run_git_command(
    args: Sequence[str],
    *,
    error_message: str,
) -> str:
    """Run one git command and return stripped stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise InfraFailure(f"{error_message}: {stderr}")
    return result.stdout.strip()


def _normalize_git_remote_url(remote_url: str) -> str:
    """Convert an origin remote into an HTTPS URL Modal can fetch."""
    normalized = remote_url.strip()
    if normalized.startswith(("https://", "http://")):
        return normalized

    ssh_match = re.match(r"^ssh://git@([^/]+)/(.+)$", normalized)
    if ssh_match:
        host, path = ssh_match.groups()
        return f"https://{host}/{path}"

    scp_match = re.match(r"^git@([^:]+):(.+)$", normalized)
    if scp_match:
        host, path = scp_match.groups()
        return f"https://{host}/{path}"

    raise InfraFailure(
        "Unsupported origin remote URL for Modal git checkout. "
        f"Use an HTTPS or Git SSH remote, got: {remote_url}"
    )


def _git_cache_namespace(remote_url: str) -> str:
    """Return a stable namespace for cached git artifacts."""
    return hashlib.sha256(remote_url.encode("utf-8")).hexdigest()[:16]


def _git_sparse_checkout_paths() -> tuple[str, ...]:
    """Return the repository paths materialized for fast-CI sandboxes."""
    return SPARSE_CHECKOUT_PATHS


def _git_source_profile_key() -> str:
    """Return a versioned cache key for the current source checkout profile."""
    digest = hashlib.sha256()
    digest.update(GIT_SOURCE_CACHE_VERSION.encode("utf-8"))
    for path in _git_sparse_checkout_paths():
        digest.update(b"\0")
        digest.update(path.encode("utf-8"))
    return digest.hexdigest()[:12]


def _resolve_git_source_ref() -> GitSourceRef:
    """Require a clean, pushed git state before running Modal fast CI."""
    dirty_output = _run_git_command(
        ["status", "--porcelain"],
        error_message="Failed to inspect git working tree",
    )
    if dirty_output:
        raise InfraFailure(
            "Modal fast CI requires a clean git working tree. "
            "Commit and push your changes first."
        )

    commit_sha = _run_git_command(
        ["rev-parse", "HEAD"],
        error_message="Failed to resolve HEAD commit",
    )
    remote_url = _normalize_git_remote_url(
        _run_git_command(
            ["remote", "get-url", "origin"],
            error_message="Failed to read git origin URL",
        )
    )
    _run_git_command(
        ["fetch", "--quiet", "origin"],
        error_message="Failed to fetch origin while validating pushed commit",
    )
    contains_output = _run_git_command(
        [
            "for-each-ref",
            "--format=%(refname)",
            "--contains",
            commit_sha,
            "refs/remotes/origin",
        ],
        error_message="Failed to verify whether HEAD is reachable from origin",
    )
    if not contains_output:
        raise InfraFailure(
            "Modal fast CI requires HEAD to be pushed to origin. "
            f"Commit {commit_sha} is not reachable from origin."
        )

    return GitSourceRef(
        commit_sha=commit_sha,
        remote_url=remote_url,
        cache_namespace=_git_cache_namespace(remote_url),
    )


def _remote_git_repo_path(source_ref: GitSourceRef) -> str:
    """Return the shared git cache path for one remote namespace."""
    return (
        f"{REMOTE_REPO_CACHE_ROOT}/"
        f"{source_ref.cache_namespace}/{_git_source_profile_key()}/workspace"
    )


def _remote_git_snapshot_path(source_ref: GitSourceRef) -> str:
    """Return the immutable snapshot path for one commit."""
    return (
        f"{REMOTE_REPO_SNAPSHOTS_ROOT}/"
        f"{source_ref.cache_namespace}/{_git_source_profile_key()}/"
        f"{source_ref.commit_sha}"
    )


def _volume_directory_contains(
    volume: Any,
    *,
    path: str,
    expected_name: str,
) -> bool:
    """Return whether a directory exists and contains the expected entry."""
    try:
        entries = volume.listdir(path)
    except Exception:
        return False
    return any(Path(entry.path).name == expected_name for entry in entries)


def _prepare_git_source_snapshot(
    *,
    app: Any,
    image: Any,
    source_ref: GitSourceRef,
    volume_name: str = DEFAULT_REPO_VOLUME_NAME,
) -> PreparedGitSourceSnapshot:
    """Ensure a shared git snapshot exists in a Modal volume."""
    import modal

    volume = modal.Volume.from_name(volume_name, create_if_missing=True)
    snapshot_path = _remote_git_snapshot_path(source_ref)
    if _volume_directory_contains(
        volume,
        path=snapshot_path,
        expected_name=".zenml-source-ready",
    ):
        log(
            "Using cached git source snapshot for commit "
            f"{source_ref.commit_sha[:12]}."
        )
        return PreparedGitSourceSnapshot(
            volume=volume,
            snapshot_path=snapshot_path,
            cache_hit=True,
            commit_sha=source_ref.commit_sha,
        )

    repo_path = _remote_git_repo_path(source_ref)
    sparse_paths = "\n".join(_git_sparse_checkout_paths())
    prep_script = """\
set -euo pipefail
repo_path="${ZENML_GIT_REPO_PATH}"
snapshot_path="${ZENML_GIT_SNAPSHOT_PATH}"
remote_url="${ZENML_GIT_REMOTE_URL}"
commit_sha="${ZENML_GIT_COMMIT_SHA}"
sparse_paths_file="${ZENML_GIT_SPARSE_PATHS_FILE}"

mkdir -p "$(dirname "$repo_path")" "$(dirname "$snapshot_path")"

if [[ ! -d "$repo_path/.git" ]]; then
  git init "$repo_path"
  git -C "$repo_path" remote add origin "$remote_url"
fi

git -C "$repo_path" remote set-url origin "$remote_url"
git -C "$repo_path" config remote.origin.promisor true
git -C "$repo_path" config remote.origin.partialclonefilter blob:none

if ! git -C "$repo_path" cat-file -e "${commit_sha}^{commit}" 2>/dev/null; then
  if ! git -C "$repo_path" fetch --prune --filter=blob:none --depth=1 origin "$commit_sha"; then
    git -C "$repo_path" fetch --prune --filter=blob:none origin
  fi
fi
git -C "$repo_path" cat-file -e "${commit_sha}^{commit}"

if [[ -d "$snapshot_path" && ! -f "$snapshot_path/.zenml-source-ready" ]]; then
  rm -rf "$snapshot_path"
fi

git -C "$repo_path" worktree prune
if [[ ! -d "$snapshot_path" ]]; then
  git -C "$repo_path" worktree add --force --detach --no-checkout "$snapshot_path" "$commit_sha"
  git -C "$snapshot_path" sparse-checkout init --cone
  mapfile -t sparse_paths < "$sparse_paths_file"
  git -C "$snapshot_path" sparse-checkout set "${sparse_paths[@]}"
  git -C "$snapshot_path" checkout --force "$commit_sha"
  touch "$snapshot_path/.zenml-source-ready"
fi
"""
    prep_env = {
        "ZENML_GIT_COMMIT_SHA": source_ref.commit_sha,
        "ZENML_GIT_REMOTE_URL": source_ref.remote_url,
        "ZENML_GIT_REPO_PATH": repo_path,
        "ZENML_GIT_SNAPSHOT_PATH": snapshot_path,
        "ZENML_GIT_SPARSE_PATHS_FILE": "/tmp/zenml-fast-ci-sparse-paths.txt",
    }
    prep_script = (
        f'cat > "$ZENML_GIT_SPARSE_PATHS_FILE" <<\'__ZENML_SPARSE_PATHS__\'\n'
        f"{sparse_paths}\n"
        "__ZENML_SPARSE_PATHS__\n"
        + prep_script
    )
    prep_mode = "incremental git fetch + sparse checkout"

    started_at = time.time()
    log(
        f"Preparing git source snapshot for commit "
        f"{source_ref.commit_sha[:12]} via {prep_mode}."
    )
    sandbox = _retry_modal_call(
        modal.Sandbox.create,
        "bash",
        "-lc",
        prep_script,
        app=app,
        image=image,
        name=f"git-source-{source_ref.commit_sha[:12]}",
        timeout=900,
        cpu=1.0,
        memory=2048,
        env=prep_env,
        volumes={REMOTE_VOLUME_ROOT: volume},
    )
    try:
        sandbox.wait()
    except Exception as error:
        raise InfraFailure(
            "Failed while preparing the git source snapshot: "
            f"{error}"
        ) from error

    stdout = _try_read_sandbox_stdout(sandbox) or ""
    stderr = ""
    stderr_stream = getattr(sandbox, "stderr", None)
    if stderr_stream is not None:
        try:
            stderr = stderr_stream.read()
        except Exception:
            stderr = ""
    exit_code = sandbox.returncode
    sandbox.terminate()
    if exit_code != 0:
        combined_logs = "\n".join(
            chunk for chunk in (stdout.strip(), stderr.strip()) if chunk
        )
        raise InfraFailure(
            "Failed while preparing the git source snapshot"
            + (f":\n{combined_logs}" if combined_logs else ".")
        )

    log(
        "Git source snapshot ready in "
        f"{time.time() - started_at:.1f}s for commit "
        f"{source_ref.commit_sha[:12]}."
    )
    return PreparedGitSourceSnapshot(
        volume=volume,
        snapshot_path=snapshot_path,
        cache_hit=False,
        commit_sha=source_ref.commit_sha,
    )


def _read_sandbox_file(sandbox: Any, path: str) -> str:
    """Read a UTF-8 file from a sandbox."""
    return _read_sandbox_bytes(sandbox, path).decode("utf-8")


def _read_sandbox_bytes(sandbox: Any, path: str) -> bytes:
    """Read binary data from a sandbox file."""
    last_error: Optional[Exception] = None
    filesystem = getattr(sandbox, "filesystem", None)
    if filesystem is not None:
        try:
            return filesystem.read_bytes(path)
        except Exception as error:
            last_error = error

    opener = getattr(sandbox, "open", None)
    if opener is None:
        if last_error is not None:
            raise last_error
        raise FileNotFoundError(path)

    with opener(path, "rb") as file_handle:
        return file_handle.read()


def _try_read_sandbox_file(sandbox: Any, path: str) -> Optional[str]:
    """Read a sandbox file if it exists."""
    try:
        return _read_sandbox_file(sandbox, path)
    except Exception:
        return None


def _try_read_sandbox_stdout(sandbox: Any) -> Optional[str]:
    """Read the sandbox stdout stream if available."""
    stdout = getattr(sandbox, "stdout", None)
    if stdout is None:
        return None

    try:
        return stdout.read()
    except Exception:
        return None


def _extract_embedded_junit(log_output: str) -> tuple[Optional[str], str]:
    """Extract an embedded JUnit payload from the batch log output."""
    start = log_output.find(JUNIT_LOG_START)
    end = log_output.find(JUNIT_LOG_END)
    if start == -1 or end == -1 or end < start:
        return None, log_output

    payload_start = start + len(JUNIT_LOG_START)
    payload = log_output[payload_start:end].strip()
    cleaned_output = (
        log_output[:start].rstrip("\n")
        + "\n"
        + log_output[end + len(JUNIT_LOG_END) :].lstrip("\n")
    ).strip()
    if not payload:
        return None, cleaned_output

    try:
        junit_xml = base64.b64decode(payload).decode("utf-8")
    except Exception:
        return None, cleaned_output
    return junit_xml, cleaned_output


def _node_id_cache_path(
    *,
    suite: str,
    collection_fingerprint: str,
    pytest_import_mode: Optional[str],
) -> Path:
    """Return the cache file path for collected node IDs."""
    import_mode = pytest_import_mode or "default"
    cache_name = f"{collection_fingerprint}-{import_mode}.json"
    return DEFAULT_NODE_ID_CACHE_DIR / suite / cache_name


def _load_cached_node_ids(
    *,
    suite: str,
    collection_fingerprint: str,
    pytest_import_mode: Optional[str],
) -> Optional[List[str]]:
    """Load cached node IDs for one suite if present."""
    cache_path = _node_id_cache_path(
        suite=suite,
        collection_fingerprint=collection_fingerprint,
        pytest_import_mode=pytest_import_mode,
    )
    if not cache_path.exists():
        return None

    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    node_ids = payload.get("node_ids")
    if not isinstance(node_ids, list) or not all(
        isinstance(node_id, str) for node_id in node_ids
    ):
        return None
    return node_ids


def _save_cached_node_ids(
    *,
    suite: str,
    collection_fingerprint: str,
    pytest_import_mode: Optional[str],
    node_ids: Sequence[str],
) -> Path:
    """Persist one suite's collected node IDs."""
    cache_path = _node_id_cache_path(
        suite=suite,
        collection_fingerprint=collection_fingerprint,
        pytest_import_mode=pytest_import_mode,
    )
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps({"node_ids": list(node_ids)}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return cache_path


def _build_modal_image(
    *,
    app: Any,
    image: Any,
    label: str,
) -> Any:
    """Eagerly build one Modal image so launches don't stall later."""
    try:
        started_at = time.time()
        log(f"Building {label} image on Modal.")
        image.build(app)
        log(
            f"{label.capitalize()} image ready in "
            f"{time.time() - started_at:.1f}s."
        )
        return image
    except Exception as error:
        raise InfraFailure(
            f"Failed while building the {label} image: {error}"
        ) from error


def _collect_node_ids_locally(
    *,
    suite: str,
    test_environment: str,
    pytest_import_mode: Optional[str],
) -> Optional[List[str]]:
    """Try to collect pytest node IDs by running pytest locally.

    Avoids spinning up a Modal sandbox, cutting collection time from ~5 minutes
    to ~20 seconds. Falls back to Modal collection if the local run fails.
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        f"tests/{suite}",
        "--collect-only",
        "-q",
        f"--environment={test_environment}",
        "--no-provision",
        "--continue-on-collection-errors",
        "--disable-warnings",
        "-p",
        "no:randomly",
        "-p",
        "no:rerunfailures",
    ]
    if pytest_import_mode:
        cmd += [f"--import-mode={pytest_import_mode}"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    # 0 = all collected, 1 = some files failed to import (partial collection),
    # 5 = no tests collected. All are usable if we got node IDs.
    if result.returncode not in (0, 1, 5):
        return None

    node_ids = _parse_collected_node_ids(result.stdout)
    return node_ids if node_ids else None


def _parse_collected_node_ids(output: str) -> List[str]:
    """Extract only concrete pytest node IDs from collect-only output."""
    node_ids: List[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or not stripped.startswith("tests/"):
            continue
        if "::" not in stripped:
            continue
        node_ids.append(stripped)
    return node_ids


def _count_duration_matches(
    node_ids: Sequence[str],
    durations: dict[str, float],
) -> int:
    """Count how many collected node IDs have historical duration data."""
    return sum(1 for node_id in node_ids if node_id in durations)


def create_batch_failure_junit(
    *,
    batch_name: str,
    node_ids: Sequence[str],
    exit_code: int,
    message: str,
) -> str:
    """Create a synthetic JUnit report for infrastructure failures."""
    tests = max(1, len(node_ids))
    escaped_message = (
        message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return (
        f'<testsuite name="{batch_name}" tests="{tests}" failures="1" errors="1">'
        '<testcase name="batch-infrastructure" classname="modal">'
        f'<error message="Sandbox exited with code {exit_code}. {escaped_message}" />'
        "</testcase>"
        "</testsuite>"
    )


def extract_failed_node_ids(junit_xml: str) -> List[str]:
    """Extract failing node ids from a JUnit XML document."""
    root = ET.fromstring(junit_xml)
    failed: List[str] = []
    for testcase in root.iter("testcase"):
        has_failure = any(
            child.tag in {"failure", "error"} for child in list(testcase)
        )
        if not has_failure:
            continue

        node_id = _node_id_from_testcase(testcase)
        if node_id:
            failed.append(node_id)
    return failed


def extract_failure_details(
    junit_xml: str,
    *,
    batch_name: str,
) -> List[FailureDetail]:
    """Extract structured failure details from a JUnit XML document."""
    root = ET.fromstring(junit_xml)
    details: List[FailureDetail] = []
    for testcase in root.iter("testcase"):
        node_id = _node_id_from_testcase(testcase)
        if not node_id:
            continue

        for child in testcase:
            if child.tag not in {"failure", "error"}:
                continue

            summary = _normalize_failure_summary(child)
            details.append(
                FailureDetail(
                    batch_name=batch_name,
                    node_id=node_id,
                    kind=_failure_kind(summary, child.tag),
                    summary=summary,
                    details=(child.text or "").strip(),
                )
            )
            break
    return details


def extract_test_durations(junit_xml: str) -> dict[str, float]:
    """Extract per-test durations from one JUnit XML document."""
    root = ET.fromstring(junit_xml)
    durations: dict[str, float] = {}
    for testcase in root.iter("testcase"):
        node_id = _node_id_from_testcase(testcase)
        if not node_id:
            continue
        duration = testcase.attrib.get("time")
        if duration is None:
            continue
        try:
            durations[node_id] = float(duration)
        except ValueError:
            continue
    return durations


def _normalize_failure_summary(element: ET.Element) -> str:
    """Collapse a failure message into one readable line."""
    message = " ".join(element.attrib.get("message", "").split())
    if message:
        return message

    for line in (element.text or "").splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("E   "):
            cleaned = cleaned[4:]
        return " ".join(cleaned.split())

    return element.tag


def _failure_kind(summary: str, fallback: str) -> str:
    """Infer a concise error kind from a failure summary."""
    if ":" not in summary:
        return fallback

    kind = summary.split(":", 1)[0].strip()
    if "." in kind:
        kind = kind.rsplit(".", 1)[-1]
    return kind or fallback


def _node_id_from_testcase(testcase: ET.Element) -> Optional[str]:
    """Map a pytest JUnit testcase back to a collectable node id."""
    classname = testcase.attrib.get("classname", "").strip()
    name = testcase.attrib.get("name", "").strip()
    if not name or classname == "modal":
        return None

    if classname.startswith("tests/"):
        return f"{classname}::{name}"

    if classname.startswith("tests."):
        parts = classname.split(".")
        for split_index in range(len(parts), 0, -1):
            candidate = REPO_ROOT / ("/".join(parts[:split_index]) + ".py")
            if candidate.exists():
                node_id = "/".join(parts[:split_index]) + ".py"
                remainder = parts[split_index:]
                if remainder:
                    return f"{node_id}::{'::'.join(remainder)}::{name}"
                return f"{node_id}::{name}"

        for split_index in range(len(parts) - 1, 0, -1):
            if not parts[split_index].startswith("test"):
                continue
            node_id = "/".join(parts[: split_index + 1]) + ".py"
            remainder = parts[split_index + 1 :]
            if remainder:
                return f"{node_id}::{'::'.join(remainder)}::{name}"
            return f"{node_id}::{name}"

        return f"{classname.replace('.', '/')}.py::{name}"

    if classname:
        return f"{classname}::{name}"
    return name


def merge_junit_xml_documents(
    documents: Sequence[str], suite_name: str
) -> str:
    """Merge multiple JUnit XML documents into one testsuites document."""
    testsuites = ET.Element("testsuites", name=suite_name)
    for document in documents:
        root = ET.fromstring(document)
        if root.tag == "testsuite":
            testsuites.append(root)
            continue
        for testsuite in root.findall("testsuite"):
            testsuites.append(testsuite)
    return ET.tostring(testsuites, encoding="unicode")


def _write_suite_junit(
    *,
    suite_name: str,
    suite_results: Sequence[BatchResult],
    suite_dir: Path,
) -> None:
    """Persist one merged JUnit report for a suite."""
    merged_junit = merge_junit_xml_documents(
        [result.junit_xml for result in suite_results],
        suite_name=suite_name,
    )
    (suite_dir / "junit.xml").write_text(merged_junit)


def write_summary(
    *,
    results: Sequence[BatchResult],
    output_path: Path,
    startup_summary: Optional[StartupSummary] = None,
) -> str:
    """Create a markdown summary for the run."""
    total_batches = len(results)
    failed_batches = sum(1 for result in results if result.exit_code != 0)
    total_failed_tests = sum(len(result.failed_node_ids) for result in results)

    lines = [
        "# Modal Fast CI Summary",
        "",
        f"- Total batches: {total_batches}",
        f"- Failed batches: {failed_batches}",
        f"- Failed tests: {total_failed_tests}",
    ]
    if startup_summary is not None:
        lines.extend(
            [
                f"- Dependency image cache: {'hit' if startup_summary.dependency_cache_hit else 'miss'}",
                "- Git source snapshot cache: "
                + ("hit" if startup_summary.source_snapshot_cache_hit else "miss"),
                "- Node ID cache: "
                + ", ".join(
                    f"`{suite}`={'hit' if hit else 'miss'}"
                    for suite, hit in sorted(
                        startup_summary.node_id_cache_hits.items()
                    )
                ),
                f"- Launch to first batch: {startup_summary.launch_to_first_batch_seconds:.1f}s",
            ]
        )
    lines.extend(["", "## Batch Timing"])
    for result in results:
        lines.append(
            f"- `{result.batch_name}`: {result.runtime_seconds:.1f}s "
            f"(expected {result.expected_duration:.1f}s)"
        )

    failure_details = _collect_failure_details(results)
    failed_node_ids = [
        node_id for result in results for node_id in result.failed_node_ids
    ]
    if failed_node_ids:
        lines.extend(["", "## Failed Tests"])
        lines.extend(f"- `{node_id}`" for node_id in failed_node_ids)
        lines.extend(["", "## Failure Groups"])
        for kind, grouped_details in _group_failure_details(failure_details):
            lines.append(
                f"### `{kind}` ({len(grouped_details)} failure"
                f"{'' if len(grouped_details) == 1 else 's'})"
            )
            lines.append(
                f"Representative message: `{grouped_details[0].summary}`"
            )
            lines.extend(
                f"- `{detail.node_id}` in `{detail.batch_name}`"
                for detail in grouped_details
            )

        lines.extend(["", "## Failed Batches"])
        for result in results:
            if result.exit_code == 0:
                continue
            batch_details = [
                detail
                for detail in failure_details
                if detail.batch_name == result.batch_name
            ]
            lines.append(
                f"### `{result.batch_name}` (exit {result.exit_code}, "
                f"{result.runtime_seconds:.1f}s)"
            )
            for detail in batch_details:
                lines.append(f"- `{detail.node_id}`: `{detail.summary}`")

    summary = "\n".join(lines) + "\n"
    output_path.write_text(summary)
    github_summary = os.getenv("GITHUB_STEP_SUMMARY")
    if github_summary:
        with open(github_summary, "a", encoding="utf-8") as summary_file:
            summary_file.write(summary)
    return summary


def write_failure_report(
    *,
    results: Sequence[BatchResult],
    output_path: Path,
) -> Optional[Path]:
    """Write a focused failure report with grouped causes and batch details."""
    failure_details = _collect_failure_details(results)
    if not failure_details:
        return None

    lines = ["# Modal Fast CI Failure Report", "", "## Failure Groups"]
    for kind, grouped_details in _group_failure_details(failure_details):
        lines.append(
            f"### `{kind}` ({len(grouped_details)} failure"
            f"{'' if len(grouped_details) == 1 else 's'})"
        )
        lines.append(f"Representative message: `{grouped_details[0].summary}`")
        lines.extend(
            f"- `{detail.node_id}` in `{detail.batch_name}`"
            for detail in grouped_details
        )

    lines.extend(["", "## Failed Batches"])
    for result in results:
        if result.exit_code == 0:
            continue
        batch_details = [
            detail
            for detail in failure_details
            if detail.batch_name == result.batch_name
        ]
        lines.append(
            f"### `{result.batch_name}` (exit {result.exit_code}, "
            f"{result.runtime_seconds:.1f}s)"
        )
        for detail in batch_details:
            lines.append(f"- `{detail.node_id}`")
            lines.append(f"Cause: `{detail.summary}`")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def format_failure_console_report(results: Sequence[BatchResult]) -> str:
    """Render a concise console digest for failing batches."""
    failure_details = _collect_failure_details(results)
    if not failure_details:
        return ""

    lines = ["Failure summary:"]
    for result in results:
        if result.exit_code == 0:
            continue
        batch_details = [
            detail
            for detail in failure_details
            if detail.batch_name == result.batch_name
        ]
        if not batch_details:
            lines.append(
                f"- `{result.batch_name}`: exit {result.exit_code} after "
                f"{result.runtime_seconds:.1f}s"
            )
            continue
        for detail in batch_details:
            lines.append(
                f"- `{result.batch_name}`: `{detail.node_id}` -> `{detail.summary}`"
            )
    return "\n".join(lines)


def _collect_failure_details(
    results: Sequence[BatchResult],
) -> List[FailureDetail]:
    """Collect failure details for all failed batches."""
    details: List[FailureDetail] = []
    for result in results:
        if result.exit_code == 0:
            continue
        details.extend(
            extract_failure_details(
                result.junit_xml, batch_name=result.batch_name
            )
        )
    return details


def _group_failure_details(
    details: Sequence[FailureDetail],
) -> List[tuple[str, List[FailureDetail]]]:
    """Group failure details by inferred error kind."""
    grouped: dict[str, List[FailureDetail]] = {}
    for detail in details:
        grouped.setdefault(detail.kind, []).append(detail)
    return sorted(
        grouped.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )


def combine_coverage_files(
    *,
    coverage_files: Sequence[Path],
    artifacts_dir: Path,
) -> Optional[Path]:
    """Combine coverage files into one XML report."""
    if not coverage_files:
        return None

    env = os.environ.copy()
    env[COVERAGE_FILE_ENV] = str(artifacts_dir / ".coverage")
    subprocess.run(
        ["coverage", "combine", *[str(path) for path in coverage_files]],
        check=True,
        cwd=REPO_ROOT,
        env=env,
    )
    output_path = artifacts_dir / "coverage.xml"
    subprocess.run(
        ["coverage", "xml", "-o", str(output_path)],
        check=True,
        cwd=REPO_ROOT,
        env=env,
    )
    return output_path


def write_duration_cache(
    *,
    results: Sequence[BatchResult],
    existing_durations: dict[str, float],
    output_path: Path,
) -> Optional[Path]:
    """Persist merged duration data for the next runner invocation."""
    durations = dict(existing_durations)
    for result in results:
        durations.update(extract_test_durations(result.junit_xml))
        if result.exit_code == 124 and result.node_ids:
            timeout_estimate = max(
                _default_duration_for_suite(result.suite),
                result.runtime_seconds / len(result.node_ids),
            )
            for node_id in result.node_ids:
                durations.setdefault(node_id, timeout_estimate)

    if not durations:
        return None

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(dict(sorted(durations.items())), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_path


def _load_duration_map(
    artifacts_dir: Path,
) -> tuple[dict[str, float], Optional[Path]]:
    """Load duration data from the best available local cache."""
    for path in (
        REPO_ROOT / ".test_durations",
        DEFAULT_DURATION_CACHE_PATH,
        artifacts_dir / ".test_durations.json",
    ):
        durations = read_durations_file(path)
        if durations:
            return durations, path
    return {}, None


def _launch_suite_batches(
    *,
    app: Any,
    image: Any,
    source_snapshot: PreparedGitSourceSnapshot,
    suite: SuiteConfig,
    batches: Sequence[ScheduledBatch],
    suite_dir: Path,
    max_workers: int,
    sandbox_cpu: float,
    sandbox_memory_mb: int,
) -> List[BatchExecution]:
    """Launch all batches for a suite concurrently."""
    executions: List[BatchExecution] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(
                _launch_batch,
                app=app,
                image=image,
                source_snapshot=source_snapshot,
                suite=suite,
                batch_index=index + 1,
                batch=batch,
                artifacts_dir=suite_dir,
                sandbox_cpu=sandbox_cpu,
                sandbox_memory_mb=sandbox_memory_mb,
            ): index
            for index, batch in enumerate(batches)
        }
        for future in as_completed(future_to_index):
            executions.append(future.result())
    return executions


def _allocate_suite_parallelism(
    *,
    suite_count: int,
    total_parallelism: int,
) -> list[int]:
    """Split a global sandbox budget across suites."""
    if suite_count <= 0:
        return []
    if total_parallelism <= 0:
        raise ValueError("total_parallelism must be greater than zero")

    base_parallelism = max(1, total_parallelism // suite_count)
    parallelism = [base_parallelism] * suite_count
    remaining = total_parallelism - sum(parallelism)

    index = 0
    while remaining > 0:
        parallelism[index] += 1
        remaining -= 1
        index = (index + 1) % suite_count

    return parallelism


def _allocate_weighted_suite_parallelism(
    *,
    suite_names: Sequence[str],
    estimated_total_durations: Sequence[float],
    total_parallelism: int,
    unit_max_sandboxes: Optional[int],
) -> list[int]:
    """Split the global sandbox budget proportionally to suite work."""
    suite_count = len(estimated_total_durations)
    if suite_count == 0:
        return []
    if total_parallelism <= 0:
        raise ValueError("total_parallelism must be greater than zero")
    if total_parallelism < suite_count:
        raise ValueError("total_parallelism must be at least the suite count")
    if len(suite_names) != suite_count:
        raise ValueError(
            "suite_names must align with estimated_total_durations"
        )

    if (
        suite_count == 2
        and set(suite_names) == {"unit", "integration"}
        and unit_max_sandboxes is not None
    ):
        unit_index = suite_names.index("unit")
        integration_index = suite_names.index("integration")
        reserved_unit_parallelism = min(
            max(1, unit_max_sandboxes),
            total_parallelism - 1,
        )
        allocations = [0] * suite_count
        allocations[unit_index] = reserved_unit_parallelism
        allocations[integration_index] = (
            total_parallelism - reserved_unit_parallelism
        )
        return allocations

    total_estimated_duration = sum(
        duration for duration in estimated_total_durations if duration > 0
    )
    if total_estimated_duration <= 0:
        return _allocate_suite_parallelism(
            suite_count=suite_count,
            total_parallelism=total_parallelism,
        )

    allocations = [1] * suite_count
    remaining = total_parallelism - suite_count
    if remaining == 0:
        return allocations

    fractional_allocations: list[tuple[float, int]] = []
    for index, duration in enumerate(estimated_total_durations):
        share = remaining * (duration / total_estimated_duration)
        whole_share = int(share)
        allocations[index] += whole_share
        fractional_allocations.append((share - whole_share, index))

    leftover = total_parallelism - sum(allocations)
    for _, index in sorted(
        fractional_allocations,
        key=lambda item: (-item[0], item[1]),
    )[:leftover]:
        allocations[index] += 1

    return allocations


def _allocate_fixed_suite_parallelism(
    *,
    suite_names: Sequence[str],
    total_parallelism: int,
    unit_max_sandboxes: Optional[int],
) -> list[int]:
    """Reserve a fixed unit budget and give the remaining slots to integration."""
    if total_parallelism <= 0:
        raise ValueError("total_parallelism must be greater than zero")

    if len(suite_names) == 1:
        return [total_parallelism]

    if set(suite_names) != {"unit", "integration"}:
        return _allocate_suite_parallelism(
            suite_count=len(suite_names),
            total_parallelism=total_parallelism,
        )

    reserved_unit_parallelism = min(
        max(1, unit_max_sandboxes or 1),
        total_parallelism - 1,
    )
    allocations = [0] * len(suite_names)
    allocations[suite_names.index("unit")] = reserved_unit_parallelism
    allocations[suite_names.index("integration")] = (
        total_parallelism - reserved_unit_parallelism
    )
    return allocations


def _finalize_suite_batches(
    *,
    executions: Sequence[BatchExecution],
    max_workers: int,
) -> List[BatchResult]:
    """Finalize all running batches concurrently."""
    results: List[BatchResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_finalize_batch, execution)
            for execution in executions
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return sorted(results, key=lambda result: result.batch_name)


def _collect_suite(
    *,
    suite: SuiteConfig,
    python_version: str,
    duration_map: dict[str, float],
) -> SuiteCollection:
    """Collect node IDs and estimate total suite duration for scheduling."""
    log(f"Starting suite '{suite.name}'.")
    collection_fingerprint = compute_collection_fingerprint(
        python_version=python_version,
        test_environment=suite.test_environment,
        suite_name=suite.name,
        pytest_import_mode=suite.pytest_import_mode,
    )
    node_id_cache_hit = False
    cached_node_ids = _load_cached_node_ids(
        suite=suite.name,
        collection_fingerprint=collection_fingerprint,
        pytest_import_mode=suite.pytest_import_mode,
    )
    if cached_node_ids is not None:
        log(f"Using cached pytest node IDs for suite '{suite.name}'.")
        node_ids = cached_node_ids
        node_id_cache_hit = True
    else:
        collect_started_at = time.time()
        log(
            f"Collecting pytest node IDs locally for suite '{suite.name}'."
        )
        node_ids = _collect_node_ids_locally(
            suite=suite.name,
            test_environment=suite.test_environment,
            pytest_import_mode=suite.pytest_import_mode,
        )
        if node_ids is None:
            raise InfraFailure(
                f"Local pytest collection failed for suite '{suite.name}'. "
                "Fix the collection error locally before running CI."
            )
        log(
            f"Collected {len(node_ids)} tests for suite '{suite.name}' "
            f"in {time.time() - collect_started_at:.1f}s."
        )
        _save_cached_node_ids(
            suite=suite.name,
            collection_fingerprint=collection_fingerprint,
            pytest_import_mode=suite.pytest_import_mode,
            node_ids=node_ids,
        )
    matched_durations = _count_duration_matches(node_ids, duration_map)
    if matched_durations == 0:
        log(
            f"No historical durations matched suite '{suite.name}'. "
            "Batching will be approximate and may be imbalanced."
        )
    else:
        log(
            f"Matched historical durations for {matched_durations}/"
            f"{len(node_ids)} tests in suite '{suite.name}'."
        )

    estimated_total_duration = sum(
        duration_map.get(node_id, suite.default_duration)
        for node_id in node_ids
    )
    return SuiteCollection(
        suite=suite,
        node_ids=node_ids,
        estimated_total_duration=estimated_total_duration,
        node_id_cache_hit=node_id_cache_hit,
    )


def _queue_batch_count(
    *,
    suite: SuiteConfig,
    suite_parallelism: int,
    node_ids: Sequence[str],
) -> int:
    """Choose how many scheduled batches to create before dispatch."""
    if suite.name == "integration":
        return min(
            len(node_ids),
            max(
                suite_parallelism,
                suite_parallelism * INTEGRATION_QUEUE_DEPTH_MULTIPLIER,
            ),
        )
    if suite.name == "unit":
        return min(
            len(node_ids),
            max(
                suite_parallelism,
                suite_parallelism * UNIT_QUEUE_DEPTH_MULTIPLIER,
            ),
        )
    return min(len(node_ids), suite_parallelism)


async def _create_sandbox_with_progress(
    *,
    create_coro: Any,
    batch_name: str,
) -> Any:
    """Wait for sandbox creation while emitting progress logs."""
    import asyncio

    started_at = time.time()
    task = asyncio.create_task(create_coro)
    while True:
        try:
            sandbox = await asyncio.wait_for(
                asyncio.shield(task),
                timeout=5,
            )
            log(
                f"Sandbox created for {batch_name} in "
                f"{time.time() - started_at:.1f}s."
            )
            return sandbox
        except asyncio.TimeoutError:
            log(
                f"Still creating sandbox for {batch_name} after "
                f"{time.time() - started_at:.1f}s. "
                "Modal is likely attaching the git snapshot volume, "
                "preparing the dependency image container, and "
                "registering the sandbox."
            )


def _build_batch_environment(
    *,
    suite: SuiteConfig,
    batch_name: str,
    source_snapshot: PreparedGitSourceSnapshot,
) -> dict[str, str]:
    """Build the environment shared by all Modal test sandboxes."""
    repository_path = source_snapshot.snapshot_path
    return {
        "ZENML_BATCH_NAME": batch_name,
        "ZENML_SUITE": suite.name,
        "ZENML_TEST_ENVIRONMENT": suite.test_environment,
        "ZENML_ARTIFACTS_DIR": REMOTE_ARTIFACTS_DIR,
        "ZENML_NODE_ID_PATH": NODE_ID_PATH,
        "ZENML_JUNIT_PATH": JUNIT_PATH,
        "ZENML_JUNIT_START": JUNIT_LOG_START,
        "ZENML_JUNIT_END": JUNIT_LOG_END,
        "ZENML_RUN_LOG_PATH": RUN_LOG_PATH,
        "ZENML_PYTEST_WORKERS": str(suite.pytest_workers),
        "ZENML_PYTEST_DIST": suite.pytest_dist,
        "ZENML_PYTEST_IMPORT_MODE": suite.pytest_import_mode or "",
        "ZENML_COLLECT_COVERAGE": "1" if suite.collect_coverage else "0",
        "ZENML_BATCH_REPOSITORY_PATH": repository_path,
        "ZENML_LOCAL_REPOSITORY_PATH": REMOTE_LOCAL_REPOSITORY_DIR,
        "ZENML_CONFIG_PATH": REMOTE_CONFIG_DIR,
        "ZENML_LOCAL_STORES_PATH": REMOTE_LOCAL_STORES_DIR,
        "PYTHONPATH": f"{repository_path}:{repository_path}/src",
        COVERAGE_FILE_ENV: REMOTE_COVERAGE_PATH,
    }


def _execute_queued_batches(
    *,
    app: Any,
    image: Any,
    source_snapshot: PreparedGitSourceSnapshot,
    suite: SuiteConfig,
    batches: Sequence[ScheduledBatch],
    suite_dir: Path,
    max_parallelism: int,
    sandbox_cpu: float,
    sandbox_memory_mb: int,
) -> List[BatchResult]:
    """Dispatch all batches concurrently using Modal's async .aio API.

    Uses asyncio.gather with a semaphore so up to max_parallelism
    sandboxes run at once. All sandbox creation happens concurrently
    on Modal's internal event loop via .aio methods.
    """
    import asyncio

    import modal

    async def _run_batch(
        semaphore: asyncio.Semaphore,
        batch_index: int,
        batch: ScheduledBatch,
    ) -> BatchResult:
        batch_name = f"{suite.name}-batch-{batch_index:02d}"
        async with semaphore:
            log(
                f"Launching {batch_name} with {len(batch.node_ids)} tests "
                f"(expected {batch.duration_seconds:.1f}s)."
            )
            _write_batch_manifest(
                artifacts_dir=suite_dir,
                batch_name=batch_name,
                suite_name=suite.name,
                batch=batch,
            )
            node_ids_b64 = base64.b64encode(
                "\n".join(batch.node_ids).encode()
            ).decode()
            embed_node_ids = len(node_ids_b64) < MODAL_ENV_PAYLOAD_MAX_BYTES
            env = _build_batch_environment(
                suite=suite,
                batch_name=batch_name,
                source_snapshot=source_snapshot,
            )
            if embed_node_ids:
                env["ZENML_NODE_IDS_B64"] = node_ids_b64
            sandbox = await _create_sandbox_with_progress(
                create_coro=modal.Sandbox.create.aio(
                    "bash",
                    "-lc",
                    (
                        'mkdir -p "$ZENML_ARTIFACTS_DIR"\n'
                        'exec > >(tee "$ZENML_RUN_LOG_PATH") 2>&1\n'
                        "set -euo pipefail\n"
                        f"{RUNNER_COMMAND}\n"
                    ),
                    app=app,
                    image=image,
                    name=batch_name,
                    timeout=suite.batch_timeout,
                    cpu=sandbox_cpu,
                    memory=sandbox_memory_mb,
                    env=env,
                    volumes={REMOTE_VOLUME_ROOT: source_snapshot.volume},
                ),
                batch_name=batch_name,
            )
            if not embed_node_ids:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: _upload_batch_node_ids(
                        sandbox=sandbox,
                        batch_name=batch_name,
                        node_ids=batch.node_ids,
                    ),
                )

            start_time = time.time()
            execution = BatchExecution(
                suite=suite,
                batch_name=batch_name,
                scheduled_batch=batch,
                sandbox=sandbox,
                artifacts_dir=suite_dir,
                start_time=start_time,
            )
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                _finalize_batch,
                execution,
            )

    async def _run_all() -> List[BatchResult]:
        semaphore = asyncio.Semaphore(max_parallelism)
        return list(
            await asyncio.gather(
                *[
                    _run_batch(semaphore, i + 1, b)
                    for i, b in enumerate(batches)
                ]
            )
        )

    results = asyncio.run(_run_all())
    return sorted(results, key=lambda result: result.batch_name)


def _run_suite(
    *,
    app: Any,
    image: Any,
    source_snapshot: PreparedGitSourceSnapshot,
    suite: SuiteConfig,
    artifacts_dir: Path,
    duration_map: dict[str, float],
    suite_parallelism: int,
    node_ids: Sequence[str],
    sandbox_cpu: float,
    sandbox_memory_mb: int,
) -> SuiteRunOutcome:
    """Execute one suite end to end inside its sandbox budget."""
    suite_dir = artifacts_dir / suite.name
    suite_dir.mkdir(parents=True, exist_ok=True)
    scheduled_batch_count = _queue_batch_count(
        suite=suite,
        suite_parallelism=suite_parallelism,
        node_ids=node_ids,
    )
    batches = schedule_batches(
        node_ids=list(node_ids),
        max_batches=scheduled_batch_count,
        durations=duration_map,
        default_duration_seconds=suite.default_duration,
        group_by_scope=(
            suite.name == "integration"
            or (suite.pytest_workers > 1 and suite.pytest_dist == "loadscope")
        ),
        max_group_size=(
            INTEGRATION_SCOPE_CHUNK_SIZE
            if suite.name == "integration"
            else None
        ),
    )
    log(
        f"Scheduled suite '{suite.name}' into {len(batches)} batches "
        f"with max parallelism {suite_parallelism}."
    )
    log(
        f"Suite '{suite.name}' settings: workers={suite.pytest_workers}, "
        f"dist={suite.pytest_dist}, "
        f"coverage={'on' if suite.collect_coverage else 'off'}."
    )
    log(
        f"Launching suite '{suite.name}' with {len(batches)} queued batches "
        f"and max parallelism {suite_parallelism}."
    )
    first_launch_started_at = time.time()
    suite_results = _execute_queued_batches(
        app=app,
        image=image,
        source_snapshot=source_snapshot,
        suite=suite,
        batches=batches,
        suite_dir=suite_dir,
        max_parallelism=suite_parallelism,
        sandbox_cpu=sandbox_cpu,
        sandbox_memory_mb=sandbox_memory_mb,
    )
    _write_suite_junit(
        suite_name=suite.name,
        suite_results=suite_results,
        suite_dir=suite_dir,
    )
    log(f"Wrote merged JUnit report for suite '{suite.name}'.")
    return SuiteRunOutcome(
        results=suite_results,
        first_launch_started_at=first_launch_started_at,
    )


def _run_suite_when_ready(
    *,
    collection_future: Future[SuiteCollection],
    source_snapshot_future: Future[PreparedGitSourceSnapshot],
    app: Any,
    image: Any,
    artifacts_dir: Path,
    duration_map: dict[str, float],
    suite_parallelism: int,
    sandbox_cpu: float,
    sandbox_memory_mb: int,
) -> tuple[SuiteCollection, SuiteRunOutcome]:
    """Launch one suite as soon as its own prerequisites are ready."""
    source_snapshot = source_snapshot_future.result()
    collection = collection_future.result()
    log(
        f"Suite '{collection.suite.name}' prerequisites ready. "
        f"Launching with reserved sandbox budget {suite_parallelism}."
    )
    outcome = _run_suite(
        app=app,
        image=image,
        source_snapshot=source_snapshot,
        suite=collection.suite,
        artifacts_dir=artifacts_dir,
        duration_map=duration_map,
        suite_parallelism=suite_parallelism,
        node_ids=collection.node_ids,
        sandbox_cpu=sandbox_cpu,
        sandbox_memory_mb=sandbox_memory_mb,
    )
    return collection, outcome


def _save_coverage_data(
    *,
    sandbox: Any,
    artifacts_dir: Path,
    batch_name: str,
    collect_coverage: bool,
) -> Optional[Path]:
    """Persist one coverage data file from a sandbox if present."""
    if not collect_coverage:
        return None

    try:
        coverage_data = _read_sandbox_bytes(sandbox, REMOTE_COVERAGE_PATH)
    except Exception:
        return None

    output_path = artifacts_dir / f".coverage.{batch_name}"
    output_path.write_bytes(coverage_data)
    return output_path


def _batch_manifest_path(*, artifacts_dir: Path, batch_name: str) -> Path:
    """Return the local manifest path for one scheduled batch."""
    return artifacts_dir / BATCH_MANIFESTS_DIRNAME / f"{batch_name}.json"


def _write_batch_manifest(
    *,
    artifacts_dir: Path,
    batch_name: str,
    suite_name: str,
    batch: ScheduledBatch,
) -> Path:
    """Persist one batch schedule so timeouts remain diagnosable."""
    manifest_path = _batch_manifest_path(
        artifacts_dir=artifacts_dir,
        batch_name=batch_name,
    )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "batch_name": batch_name,
                "suite": suite_name,
                "expected_duration_seconds": batch.duration_seconds,
                "node_count": len(batch.node_ids),
                "node_ids": list(batch.node_ids),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return manifest_path


def _upload_batch_node_ids(
    *,
    sandbox: Any,
    batch_name: str,
    node_ids: Sequence[str],
) -> None:
    """Upload batch node IDs into the sandbox via filesystem API."""
    payload = "".join(f"{node_id}\n" for node_id in node_ids)
    filesystem = getattr(sandbox, "filesystem", None)
    if filesystem is not None:
        try:
            filesystem.write_text(NODE_ID_PATH, payload)
            return
        except Exception:
            pass

    heredoc = "__ZENML_BATCH_NODE_IDS__"
    chunk_size = 50000
    if len(payload) <= chunk_size:
        process = sandbox.exec(
            "bash",
            "-lc",
            (
                f"cat > {shlex.quote(NODE_ID_PATH)} <<'{heredoc}'\n"
                f"{payload}"
                f"{heredoc}\n"
            ),
            timeout=BATCH_NODE_UPLOAD_TIMEOUT_SECONDS,
        )
        exit_code = process.wait()
        if exit_code != 0:
            stdout = process.stdout.read()
            stderr = process.stderr.read()
            raise InfraFailure(
                f"Failed to upload node IDs for {batch_name}.\n"
                f"stdout:\n{stdout}\n\nstderr:\n{stderr}"
            )
        return

    lines = payload.splitlines(keepends=True)
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for line in lines:
        if current_size + len(line) > chunk_size and current:
            chunks.append("".join(current))
            current = []
            current_size = 0
        current.append(line)
        current_size += len(line)
    if current:
        chunks.append("".join(current))

    for i, chunk in enumerate(chunks):
        redirect = ">" if i == 0 else ">>"
        process = sandbox.exec(
            "bash",
            "-lc",
            (
                f"cat {redirect} {shlex.quote(NODE_ID_PATH)} <<'{heredoc}'\n"
                f"{chunk}"
                f"{heredoc}\n"
            ),
            timeout=BATCH_NODE_UPLOAD_TIMEOUT_SECONDS,
        )
        exit_code = process.wait()
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        if exit_code != 0:
            raise InfraFailure(
                f"Failed to upload node IDs for {batch_name} (chunk {i + 1}).\n"
                f"stdout:\n{stdout}\n\nstderr:\n{stderr}"
            )


def _launch_batch(
    *,
    app: Any,
    image: Any,
    source_snapshot: PreparedGitSourceSnapshot,
    suite: SuiteConfig,
    batch_index: int,
    batch: ScheduledBatch,
    artifacts_dir: Path,
    sandbox_cpu: float,
    sandbox_memory_mb: int,
) -> BatchExecution:
    """Launch one scheduled batch in Modal."""
    import modal

    batch_name = f"{suite.name}-batch-{batch_index:02d}"
    log(
        f"Launching {batch_name} with {len(batch.node_ids)} tests "
        f"(expected {batch.duration_seconds:.1f}s)."
    )
    _write_batch_manifest(
        artifacts_dir=artifacts_dir,
        batch_name=batch_name,
        suite_name=suite.name,
        batch=batch,
    )
    sandbox = _retry_modal_call(
        modal.Sandbox.create,
        "bash",
        "-lc",
        (
            'mkdir -p "$ZENML_ARTIFACTS_DIR"\n'
            'exec > >(tee "$ZENML_RUN_LOG_PATH") 2>&1\n'
            "set -euo pipefail\n"
            f"{RUNNER_COMMAND}\n"
        ),
        app=app,
        image=image,
        name=batch_name,
        timeout=suite.batch_timeout,
        cpu=sandbox_cpu,
        memory=sandbox_memory_mb,
        env=_build_batch_environment(
            suite=suite,
            batch_name=batch_name,
            source_snapshot=source_snapshot,
        ),
        volumes={REMOTE_VOLUME_ROOT: source_snapshot.volume},
    )
    try:
        _upload_batch_node_ids(
            sandbox=sandbox,
            batch_name=batch_name,
            node_ids=batch.node_ids,
        )
    except Exception:
        sandbox.terminate()
        raise
    start_time = time.time()
    return BatchExecution(
        suite=suite,
        batch_name=batch_name,
        scheduled_batch=batch,
        sandbox=sandbox,
        artifacts_dir=artifacts_dir,
        start_time=start_time,
    )


def _finalize_batch(execution: BatchExecution) -> BatchResult:
    """Wait for one running batch and collect its artifacts."""
    log(f"Waiting for {execution.batch_name} to finish.")
    timed_out = False
    try:
        execution.sandbox.wait()
    except Exception as error:
        if error.__class__.__name__ == "SandboxTimeoutError":
            timed_out = True
        else:
            raise InfraFailure(
                f"Failed while waiting for {execution.batch_name}: {error}"
            ) from error

    exit_code = execution.sandbox.returncode
    if exit_code is None:
        exit_code = 124 if timed_out else -1
    runtime_seconds = time.time() - execution.start_time

    log_output = _try_read_sandbox_stdout(execution.sandbox)
    if log_output is None:
        log_output = (
            _try_read_sandbox_file(execution.sandbox, RUN_LOG_PATH) or ""
        )

    embedded_junit, log_output = _extract_embedded_junit(log_output)
    junit_xml = embedded_junit or _try_read_sandbox_file(
        execution.sandbox, JUNIT_PATH
    )
    if junit_xml is None:
        junit_xml = create_batch_failure_junit(
            batch_name=execution.batch_name,
            node_ids=execution.scheduled_batch.node_ids,
            exit_code=exit_code,
            message=(
                "Pytest exited before writing JUnit output. "
                "This usually indicates an import error, crash, or timeout."
                if not timed_out
                else "Modal terminated the sandbox after the batch timeout."
            ),
        )
        failed_node_ids = list(execution.scheduled_batch.node_ids)
    else:
        failed_node_ids = extract_failed_node_ids(junit_xml)

    coverage_path = _save_coverage_data(
        sandbox=execution.sandbox,
        artifacts_dir=execution.artifacts_dir,
        batch_name=execution.batch_name,
        collect_coverage=execution.suite.collect_coverage,
    )
    execution.sandbox.terminate()
    status = "passed" if exit_code == 0 else f"failed (exit {exit_code})"
    log(
        f"Finished {execution.batch_name}: {status} in {runtime_seconds:.1f}s "
        f"with {len(failed_node_ids)} failed tests."
    )

    return BatchResult(
        suite=execution.suite.name,
        batch_name=execution.batch_name,
        node_ids=list(execution.scheduled_batch.node_ids),
        expected_duration=execution.scheduled_batch.duration_seconds,
        runtime_seconds=runtime_seconds,
        exit_code=exit_code,
        junit_xml=junit_xml,
        failed_node_ids=failed_node_ids,
        log_output=log_output,
        coverage_path=coverage_path,
    )


def run_modal_fast_ci(args: argparse.Namespace) -> RunnerSummary:
    """Execute the full Modal-backed Linux fast CI flow."""
    import modal

    modal.enable_output()
    run_started_at = time.time()
    artifacts_dir = args.artifacts_dir.resolve()
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    log(f"Writing artifacts to {artifacts_dir}.")
    suite_configs = suite_configs_from_args(args)
    unit_max_sandboxes = args.unit_max_sandboxes
    if unit_max_sandboxes is None and {
        suite.name for suite in suite_configs
    } == {"unit", "integration"}:
        unit_max_sandboxes = 1
    duration_map: dict[str, float]
    duration_source: Optional[Path]
    if args.use_existing_test_durations:
        duration_map, duration_source = _load_duration_map(artifacts_dir)
    else:
        duration_map, duration_source = {}, None
    if duration_source is not None:
        log(f"Loaded historical durations from {duration_source}.")
    else:
        log("No historical duration cache found.")

    git_source_ref = _resolve_git_source_ref()
    log(
        "Using pushed git commit "
        f"{git_source_ref.commit_sha[:12]} from origin for Modal sandboxes."
    )
    log(f"Using Modal app name '{DEFAULT_MODAL_APP_NAME}'.")
    app = modal.App.lookup(DEFAULT_MODAL_APP_NAME, create_if_missing=True)
    dependency_resolution: ResolvedDependencyImage = resolve_dependency_image(
        python_version=args.python_version
    )

    results: List[BatchResult] = []
    suite_startup: dict[str, bool] = {}
    first_launch_started_at: Optional[float] = None
    source_snapshot: Optional[PreparedGitSourceSnapshot] = None
    try:
        with ThreadPoolExecutor(
            max_workers=max(2, len(suite_configs) + 1)
        ) as executor:
            if dependency_resolution.cache_hit:
                dependency_image_future: Future[Any] = Future()
                dependency_image_future.set_result(
                    dependency_resolution.image
                )
            else:
                dependency_image_future = executor.submit(
                    _build_modal_image,
                    app=app,
                    image=dependency_resolution.image,
                    label="dependency",
                )
            future_to_suite = {
                executor.submit(
                    _collect_suite,
                    suite=suite,
                    python_version=args.python_version,
                    duration_map=duration_map,
                ): suite.name
                for suite in suite_configs
            }
            built_dependency_image = dependency_image_future.result()
            if not dependency_resolution.cache_hit:
                dependency_image_id = getattr(
                    built_dependency_image, "object_id", None
                )
                if dependency_image_id:
                    save_cached_manifest(
                        CachedImageManifest(
                            fingerprint=dependency_resolution.fingerprint,
                            image_id=dependency_image_id,
                            python_version=args.python_version,
                        )
                    )
            source_snapshot_future = executor.submit(
                _prepare_git_source_snapshot,
                app=app,
                image=built_dependency_image,
                source_ref=git_source_ref,
            )
            suite_parallelism = _allocate_fixed_suite_parallelism(
                suite_names=[suite.name for suite in suite_configs],
                total_parallelism=args.max_sandboxes,
                unit_max_sandboxes=unit_max_sandboxes,
            )
            log(
                "Suite sandbox budgets: "
                + ", ".join(
                    f"{suite.name}={parallelism}"
                    for suite, parallelism in zip(
                        suite_configs,
                        suite_parallelism,
                    )
                )
                + "."
            )
            suite_run_futures = {
                executor.submit(
                    _run_suite_when_ready,
                    collection_future=collection_future,
                    source_snapshot_future=source_snapshot_future,
                    app=app,
                    image=built_dependency_image,
                    artifacts_dir=artifacts_dir,
                    duration_map=duration_map,
                    suite_parallelism=parallelism,
                    sandbox_cpu=args.sandbox_cpu,
                    sandbox_memory_mb=args.sandbox_memory_mb,
                ): suite_name
                for (collection_future, suite_name), parallelism in zip(
                    future_to_suite.items(),
                    suite_parallelism,
                )
            }

            for future in as_completed(suite_run_futures):
                collection, outcome = future.result()
                suite_startup[collection.suite.name] = (
                    collection.node_id_cache_hit
                )
                if (
                    first_launch_started_at is None
                    or (
                        outcome.first_launch_started_at is not None
                        and outcome.first_launch_started_at
                        < first_launch_started_at
                    )
                ):
                    first_launch_started_at = outcome.first_launch_started_at
                results.extend(outcome.results)

            source_snapshot = source_snapshot_future.result()
    except InfraFailure:
        log("Encountered a Modal infrastructure failure.")
        raise

    results.sort(key=lambda result: (result.suite, result.batch_name))

    coverage_files = [
        result.coverage_path
        for result in results
        if result.coverage_path is not None
    ]
    combine_coverage_files(
        coverage_files=[path for path in coverage_files if path is not None],
        artifacts_dir=artifacts_dir,
    )
    if coverage_files:
        log("Combined coverage data.")
    duration_cache_path = write_duration_cache(
        results=results,
        existing_durations=duration_map,
        output_path=DEFAULT_DURATION_CACHE_PATH,
    )
    if duration_cache_path is not None:
        log(f"Updated duration cache at {duration_cache_path}.")
    startup_summary = StartupSummary(
        dependency_cache_hit=dependency_resolution.cache_hit,
        source_snapshot_cache_hit=(
            False if source_snapshot is None else source_snapshot.cache_hit
        ),
        node_id_cache_hits={
            suite_name: node_id_cache_hit
            for suite_name, node_id_cache_hit in suite_startup.items()
        },
        launch_to_first_batch_seconds=(
            0.0
            if first_launch_started_at is None
            else first_launch_started_at - run_started_at
        ),
    )
    write_summary(
        results=results,
        output_path=artifacts_dir / "summary.md",
        startup_summary=startup_summary,
    )
    log("Wrote run summary.")
    failure_report_path = write_failure_report(
        results=results,
        output_path=artifacts_dir / "failures.md",
    )
    if failure_report_path is not None:
        log(f"Wrote failure report to {failure_report_path}.")
    return RunnerSummary(results=results, startup_summary=startup_summary)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    log(
        "Starting Modal fast CI run for suites "
        f"{', '.join(args.suite)} on Python {args.python_version}."
    )
    try:
        summary = run_modal_fast_ci(args)
    except InfraFailure as error:
        print(str(error), file=sys.stderr)
        return RUNNER_EXIT_INFRA_FAILURE

    if any(result.exit_code != 0 for result in summary.results):
        console_report = format_failure_console_report(summary.results)
        if console_report:
            print(console_report)
        log("Completed with test failures.")
        return RUNNER_EXIT_TEST_FAILURE
    log("Completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
