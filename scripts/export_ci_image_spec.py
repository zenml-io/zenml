#!/usr/bin/env python3
"""Export the ZenML CI image dependency spec for Modal-backed unit tests."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

BASE_OPTIONAL_DEPENDENCY_GROUPS = (
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

BASE_APT_PACKAGES = ("git", "curl", "graphviz")
BASE_INTEGRATION_IGNORES = [
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
]


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _load_pyproject() -> dict:
    with PYPROJECT_PATH.open("rb") as pyproject_file:
        return tomllib.load(pyproject_file)


def _base_requirements() -> list[str]:
    pyproject = _load_pyproject()
    project = pyproject["project"]
    requirements = list(project["dependencies"])
    optional_dependencies = project["optional-dependencies"]

    for group in BASE_OPTIONAL_DEPENDENCY_GROUPS:
        requirements.extend(optional_dependencies[group])

    filtered_requirements = [
        requirement
        for requirement in requirements
        if not requirement.lower().startswith("zenml[")
    ]
    return _dedupe_preserving_order(filtered_requirements)


def _integration_ignore_list(python_version: str, target_os: str) -> list[str]:
    ignores = list(BASE_INTEGRATION_IGNORES)

    if python_version in {"3.12", "3.13"}:
        ignores.extend(["tensorflow", "deepchecks"])

    if target_os.lower() == "windows":
        ignores.extend(["pytorch", "neural_prophet", "pytorch_lightning"])

    return _dedupe_preserving_order(ignores)


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd or REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        if exc.stdout:
            print(exc.stdout, file=sys.stderr, end="")
        if exc.stderr:
            print(exc.stderr, file=sys.stderr, end="")
        raise


def _export_integration_spec(
    *,
    base_requirements: list[str],
    ignore_integrations: list[str],
    target_os: str,
) -> tuple[list[str], list[str]]:
    uv_path = shutil.which("uv")
    if not uv_path:
        raise RuntimeError("uv must be available to export the CI image spec.")

    with tempfile.TemporaryDirectory(prefix="zenml-modal-spec-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        venv_dir = temp_dir / "venv"
        requirements_path = temp_dir / "base-requirements.txt"
        requirements_path.write_text("\n".join(base_requirements) + "\n")

        _run([uv_path, "venv", str(venv_dir)])
        python_bin = _venv_python(venv_dir)
        _run(
            [
                uv_path,
                "pip",
                "install",
                "--python",
                str(python_bin),
                "-r",
                str(requirements_path),
            ]
        )
        _run(
            [
                uv_path,
                "pip",
                "install",
                "--python",
                str(python_bin),
                "-e",
                ".",
                "--no-deps",
            ]
        )

        script = textwrap.dedent(
            """
            import json
            from zenml.integrations.registry import integration_registry

            ignored = set(json.loads(__import__("os").environ["ZENML_IGNORED_INTEGRATIONS"]))
            target_os = __import__("os").environ["ZENML_TARGET_OS"]

            requirements = []
            apt_packages = []
            for name in sorted(integration_registry.list_integration_names):
                if name in ignored:
                    continue
                requirements.extend(
                    integration_registry.select_integration_requirements(
                        name, target_os=target_os
                    )
                )
                apt_packages.extend(integration_registry.integrations[name].APT_PACKAGES)

            print(
                json.dumps(
                    {
                        "requirements": requirements,
                        "apt_packages": apt_packages,
                    }
                )
            )
            """
        ).strip()
        env = os.environ.copy()
        env["ZENML_IGNORED_INTEGRATIONS"] = json.dumps(ignore_integrations)
        env["ZENML_TARGET_OS"] = target_os

        result = _run([str(python_bin), "-c", script], env=env)
        exported = json.loads(result.stdout)

    return (
        _dedupe_preserving_order(list(exported["requirements"])),
        _dedupe_preserving_order(list(exported["apt_packages"])),
    )


def export_ci_image_spec(args: argparse.Namespace) -> int:
    base_requirements = _base_requirements()
    all_requirements = list(base_requirements)
    all_apt_packages = list(BASE_APT_PACKAGES)

    if args.install_integrations == "yes":
        ignore_integrations = _integration_ignore_list(
            python_version=args.python_version,
            target_os=args.target_os,
        )
        integration_requirements, integration_apt_packages = _export_integration_spec(
            base_requirements=base_requirements,
            ignore_integrations=ignore_integrations,
            target_os=args.target_os,
        )
        all_requirements.extend(integration_requirements)
        all_requirements.extend(
            [
                "pyyaml>=6.0.1",
                "pyopenssl",
                "typing-extensions",
                "maison<2",
            ]
        )
        all_apt_packages.extend(integration_apt_packages)

    deduped_requirements = _dedupe_preserving_order(all_requirements)
    deduped_apt_packages = _dedupe_preserving_order(all_apt_packages)

    requirements_output = Path(args.output_requirements).resolve()
    requirements_output.parent.mkdir(parents=True, exist_ok=True)
    requirements_output.write_text("\n".join(deduped_requirements) + "\n")

    apt_output = Path(args.output_apt_packages).resolve()
    apt_output.parent.mkdir(parents=True, exist_ok=True)
    apt_output.write_text("\n".join(deduped_apt_packages) + "\n")

    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-version", default="3.11")
    parser.add_argument("--target-os", default="Linux")
    parser.add_argument(
        "--install-integrations",
        choices=("yes", "no"),
        default="yes",
    )
    parser.add_argument("--output-requirements", required=True)
    parser.add_argument("--output-apt-packages", required=True)
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return export_ci_image_spec(args)


if __name__ == "__main__":
    raise SystemExit(main())
