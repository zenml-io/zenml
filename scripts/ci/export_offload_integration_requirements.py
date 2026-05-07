"""Export integration requirements for the offload CI image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

IGNORED_INTEGRATIONS = {
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
    "tensorflow",
    "deepchecks",
}

SUPPLEMENTAL_REQUIREMENTS = [
    "pyyaml>=6.0.1",
    "pyopenssl",
    "typing-extensions",
    "maison<2",
]


def export_requirements(output_file: Path) -> None:
    """Export the requirements used by the offload Modal image."""
    from zenml.integrations.registry import integration_registry

    output_file.parent.mkdir(parents=True, exist_ok=True)
    requirements: list[str] = []
    for integration_name in sorted(integration_registry.integrations):
        if integration_name in IGNORED_INTEGRATIONS:
            continue
        requirements.extend(
            integration_registry.select_integration_requirements(
                integration_name
            )
        )

    requirements.extend(SUPPLEMENTAL_REQUIREMENTS)
    output_file.write_text("\n".join(requirements) + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)
    export_requirements(args.output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
