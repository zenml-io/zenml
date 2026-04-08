"""Combine coverage files downloaded by offload into a single report.

Offload downloads artifacts into:
    {output_dir}/{sandbox_id}/{batch_id}/.coverage*

This script finds all .coverage* files, copies them to a staging dir,
and runs `coverage combine` + `coverage xml`.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("test-results/modal-fast-ci")
DEFAULT_COVERAGE_XML = Path("coverage.xml")


def combine_coverage(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    coverage_xml: Path = DEFAULT_COVERAGE_XML,
) -> int:
    coverage_files = [
        f
        for f in output_dir.rglob(".coverage*")
        if f.is_file() and not f.name.endswith(".xml")
    ]

    if not coverage_files:
        print("No coverage files found.", file=sys.stderr)
        return 0

    with tempfile.TemporaryDirectory() as staging:
        staging_path = Path(staging)
        for i, src in enumerate(coverage_files):
            shutil.copy2(src, staging_path / f".coverage.{i}")

        print(f"Combining {len(coverage_files)} coverage files.")
        result = subprocess.run(["coverage", "combine"], cwd=staging_path)
        if result.returncode != 0:
            print("coverage combine failed.", file=sys.stderr)
            return result.returncode

        combined = staging_path / ".coverage"
        if not combined.exists():
            print("No combined .coverage file produced.", file=sys.stderr)
            return 1

        result = subprocess.run(
            ["coverage", "xml", "-o", str(coverage_xml.resolve())],
            cwd=staging_path,
        )
        if result.returncode != 0:
            print("coverage xml failed.", file=sys.stderr)
            return result.returncode

    print(f"Coverage report written to {coverage_xml}.")
    return 0


if __name__ == "__main__":
    sys.exit(combine_coverage())
