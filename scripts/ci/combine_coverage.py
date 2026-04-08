"""Combine coverage files downloaded by offload into a single report.

Offload downloads artifacts into:
    {output_dir}/{sandbox_id}/{batch_id}/.coverage*

This script finds all .coverage* files, copies them to a flat directory,
and runs `coverage combine` + `coverage xml`.
"""

import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("test-results/modal-fast-ci")
DEFAULT_COVERAGE_XML = Path("coverage.xml")


def combine_coverage(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    coverage_xml: Path = DEFAULT_COVERAGE_XML,
) -> int:
    coverage_files = list(output_dir.rglob(".coverage*"))
    coverage_files = [
        f
        for f in coverage_files
        if f.is_file() and not f.name.endswith(".xml")
    ]

    if not coverage_files:
        print("No coverage files found.", file=sys.stderr)
        return 0

    staging = output_dir / ".coverage-staging"
    staging.mkdir(parents=True, exist_ok=True)

    for i, src in enumerate(coverage_files):
        dest = staging / f".coverage.{i}"
        shutil.copy2(src, dest)

    print(f"Combining {len(coverage_files)} coverage files.")
    result = subprocess.run(
        ["coverage", "combine"],
        cwd=staging,
    )
    if result.returncode != 0:
        print("coverage combine failed.", file=sys.stderr)
        return result.returncode

    combined = staging / ".coverage"
    if not combined.exists():
        print("No combined .coverage file produced.", file=sys.stderr)
        return 1

    result = subprocess.run(
        ["coverage", "xml", "-o", str(coverage_xml.resolve())],
        cwd=staging,
    )
    if result.returncode != 0:
        print("coverage xml failed.", file=sys.stderr)
        return result.returncode

    print(f"Coverage report written to {coverage_xml}.")
    shutil.rmtree(staging, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(combine_coverage())
