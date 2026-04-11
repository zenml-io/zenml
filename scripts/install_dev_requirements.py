"""Shared requirement export helpers for dev installs and fast CI."""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEV_PROJECT_EXTRAS = (
    "server",
    "templates",
    "terraform",
    "secrets-aws",
    "secrets-gcp",
    "secrets-azure",
    "secrets-hashicorp",
    "s3fs",
    "gcsfs",
    "adlfs",
    "dev",
    "connectors-aws",
    "connectors-gcp",
    "connectors-azure",
    "azureml",
    "sagemaker",
    "vertex",
)
PINNED_REQUIREMENTS = (
    "pyyaml>=6.0.1",
    "pyopenssl",
    "typing-extensions",
    "maison<2",
)
BASE_IGNORED_INTEGRATIONS = (
    "feast",
    "label_studio",
    "bentoml",
    "seldon",
    "pycaret",
    "skypilot_aws",
    "skypilot_gcp",
    "skypilot_azure",
    "skypilot_kubernetes",
    "skypilot_lambda",
    "pigeon",
    "prodigy",
    "argilla",
    "vllm",
)
PY312_PLUS_IGNORED_INTEGRATIONS = (
    "tensorflow",
    "deepchecks",
)
WINDOWS_IGNORED_INTEGRATIONS = (
    "pytorch",
    "neural_prophet",
    "pytorch_lightning",
)
TARGET_PLATFORM_BY_OS = {
    "linux": "linux",
    "windows": "windows",
    "darwin": "macos",
    "macos": "macos",
}


def current_python_version() -> str:
    """Return the current interpreter version as major.minor."""
    return ".".join(map(str, sys.version_info[:2]))


def current_target_os() -> str:
    """Return the current operating system name."""
    return platform.system()


def build_editable_project_spec(
    project_path: str = ".",
    extras: Sequence[str] = DEFAULT_DEV_PROJECT_EXTRAS,
) -> str:
    """Return the editable install spec used by the dev install script."""
    return f"{project_path}[{','.join(extras)}]"


def ignored_integrations_for_dev_install(
    *,
    python_version: str,
    target_os: str,
) -> list[str]:
    """Return integrations intentionally excluded from dev installs."""
    ignored = list(BASE_IGNORED_INTEGRATIONS)
    major, minor = _parse_python_version(python_version)
    if (major, minor) >= (3, 12):
        ignored.extend(PY312_PLUS_IGNORED_INTEGRATIONS)
    if target_os.lower() == "windows":
        ignored.extend(WINDOWS_IGNORED_INTEGRATIONS)
    return sorted(set(ignored))


def collect_integration_requirements(
    *,
    python_version: str,
    target_os: str,
    root: Path = REPO_ROOT,
) -> list[str]:
    """Collect integration requirements without installing the local project."""
    registry = _load_integration_registry(root)
    ignored = set(
        ignored_integrations_for_dev_install(
            python_version=python_version,
            target_os=target_os,
        )
    )
    requirements: list[str] = []
    for name, integration in sorted(registry.integrations.items()):
        if name in ignored:
            continue
        requirements.extend(
            integration.get_requirements(
                target_os=target_os,
                python_version=python_version,
            )
        )
    return dedupe_requirements(requirements)


def write_integration_input_requirements(
    *,
    python_version: str,
    target_os: str,
    output_path: Path,
    include_project_spec: bool,
    project_path: str = ".",
    root: Path = REPO_ROOT,
) -> Path:
    """Write the top-level requirements used by the dev install workflow."""
    requirements = collect_integration_requirements(
        python_version=python_version,
        target_os=target_os,
        root=root,
    )
    requirements.extend(PINNED_REQUIREMENTS)
    if include_project_spec:
        requirements.append(build_editable_project_spec(project_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(dedupe_requirements(requirements)) + "\n",
        encoding="utf-8",
    )
    return output_path


def build_compile_requirements_command(
    *,
    python_version: str,
    target_os: str,
    target_platform: str | None,
    output_path: Path,
    input_paths: Sequence[Path],
    extras: Sequence[str] = DEFAULT_DEV_PROJECT_EXTRAS,
) -> list[str]:
    """Build the uv compile command for a target platform."""
    command = [
        "uv",
        "pip",
        "compile",
        "pyproject.toml",
        *[str(path) for path in input_paths],
        "--format",
        "requirements.txt",
        "--output-file",
        str(output_path),
        "--python-version",
        python_version,
        "--python-platform",
        target_platform or normalize_target_platform(target_os),
        "--no-header",
        "--no-annotate",
        "--no-emit-package",
        "zenml",
    ]
    for extra in extras:
        command.extend(["--extra", extra])
    return command


def write_compiled_requirements(
    *,
    python_version: str,
    target_os: str,
    target_platform: str | None,
    output_path: Path,
    include_integrations: bool,
    root: Path = REPO_ROOT,
) -> Path:
    """Write a fully resolved third-party requirements file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_paths: list[Path] = []
        if include_integrations:
            integration_input_path = (
                Path(tmp_dir) / "integration-input-requirements.txt"
            )
            write_integration_input_requirements(
                python_version=python_version,
                target_os=target_os,
                output_path=integration_input_path,
                include_project_spec=False,
                root=root,
            )
            input_paths.append(integration_input_path)

        subprocess.run(
            build_compile_requirements_command(
                python_version=python_version,
                target_os=target_os,
                target_platform=target_platform,
                output_path=output_path,
                input_paths=input_paths,
            ),
            check=True,
            cwd=root,
        )

    return output_path


def dedupe_requirements(requirements: Iterable[str]) -> list[str]:
    """Preserve order while removing duplicate or blank requirement lines."""
    seen: set[str] = set()
    deduped: list[str] = []
    for requirement in requirements:
        normalized = requirement.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def normalize_target_platform(target_os: str) -> str:
    """Map a host OS label to a uv-compatible target platform."""
    try:
        return TARGET_PLATFORM_BY_OS[target_os.lower()]
    except KeyError as error:
        raise ValueError(f"Unsupported target OS: {target_os}") from error


def _load_integration_registry(root: Path):
    """Load the integration registry from local source."""
    src_path = str(root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from zenml.integrations.registry import integration_registry

    return integration_registry


def _parse_python_version(python_version: str) -> tuple[int, int]:
    """Parse a major.minor Python version string."""
    version_parts = python_version.split(".")
    major = int(version_parts[0])
    minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    return major, minor


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for requirement export helpers."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    editable_spec = subparsers.add_parser(
        "editable-spec",
        help="Print the editable install spec for ZenML dev installs.",
    )
    editable_spec.add_argument(
        "--project-path",
        default=".",
        help="Project path prefix used in the editable install spec.",
    )

    integration_input = subparsers.add_parser(
        "write-integration-input",
        help="Write the top-level integration requirements file.",
    )
    _add_common_export_arguments(integration_input)
    integration_input.add_argument(
        "--include-project-spec",
        choices=("yes", "no"),
        default="yes",
        help="Append the editable ZenML project spec to the output.",
    )
    integration_input.add_argument(
        "--project-path",
        default=".",
        help="Project path prefix used in the editable install spec.",
    )

    compiled = subparsers.add_parser(
        "write-compiled-requirements",
        help="Write a fully resolved third-party requirements file.",
    )
    _add_common_export_arguments(compiled)
    compiled.add_argument(
        "--include-integrations",
        choices=("yes", "no"),
        default="yes",
        help="Include integration dependencies in the compiled output.",
    )

    return parser


def _add_common_export_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared CLI arguments used by file-writing commands."""
    parser.add_argument(
        "--output-file",
        required=True,
        type=Path,
        help="Path to the generated requirements file.",
    )
    parser.add_argument(
        "--python-version",
        default=current_python_version(),
        help="Target Python version in major.minor format.",
    )
    parser.add_argument(
        "--target-os",
        default=current_target_os(),
        help="Target operating system name.",
    )
    parser.add_argument(
        "--target-platform",
        default=None,
        help="Explicit uv target platform override.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requirements helper CLI."""
    args = _build_parser().parse_args(argv)

    if args.command == "editable-spec":
        print(build_editable_project_spec(project_path=args.project_path))
        return 0

    if args.command == "write-integration-input":
        write_integration_input_requirements(
            python_version=args.python_version,
            target_os=args.target_os,
            output_path=args.output_file,
            include_project_spec=args.include_project_spec == "yes",
            project_path=args.project_path,
        )
        return 0

    if args.command == "write-compiled-requirements":
        write_compiled_requirements(
            python_version=args.python_version,
            target_os=args.target_os,
            target_platform=args.target_platform,
            output_path=args.output_file,
            include_integrations=args.include_integrations == "yes",
        )
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
