"""Trusted final-state grading in a fresh runtime after terminal shutdown."""

import io
import tarfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from typing import Any

from .environment import MAX_ARCHIVE, TerminalEnvironment


def grade_environment(
    env: TerminalEnvironment,
    test_path: Path,
    protected_sources: dict[str, str],
) -> dict[str, Any]:
    """Stop task processes and grade home data in an original clean image.

    Args:
        env: Active environment whose containers are tracked for cleanup.
        test_path: Trusted host-side final-state test, hidden during interaction.
        protected_sources: Paths and expected hashes of immutable source inputs.

    Returns:
        Raw reward, independent integrity audit, and infrastructure errors.
        Ordinary grading and cleanup exceptions are captured in this result.
    """  # noqa: DOC501,DOC503
    result: dict[str, Any] = {
        "raw_reward": None,
        "audited_valid": False,
        "protected_sources": {},
        "infrastructure_error": None,
    }
    try:
        archive = env.home_snapshot()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            members = tar.getmembers()
            for member in members:
                archive_path = PurePosixPath(member.name)
                if (
                    archive_path.is_absolute()
                    or ".." in archive_path.parts
                    or not (member.isfile() or member.isdir())
                ):
                    raise ValueError("Unsafe archive member: " + member.name)
            if sum(member.size for member in members) > MAX_ARCHIVE:
                raise ValueError("Unpacked home exceeds archive limit")
        for path, expected in protected_sources.items():
            try:
                actual = env.source_hash(path)
            except (RuntimeError, ValueError):
                actual = None
            result["protected_sources"][path] = {
                "expected": expected,
                "actual": actual,
                "unchanged": actual == expected,
            }
        exit_code, output, xml = env.verify_snapshot(archive, test_path)
        result["verifier_exit_code"] = exit_code
        if exit_code not in (0, 1):
            raise RuntimeError(
                f"Verifier infrastructure failure: pytest exit {exit_code}"
            )
        result["verifier_output"] = output
        result["junit_xml"] = xml.decode(errors="replace")
        cases = ET.fromstring(xml).findall(".//testcase")
        counts = {
            name: sum(case.find(name) is not None for case in cases)
            for name in ("failure", "error", "skipped")
        }
        result["test_counts"] = {"total": len(cases), **counts}
        result["raw_reward"] = int(exit_code == 0)
        result["audited_valid"] = bool(
            exit_code == 0
            and cases
            and not any(counts.values())
            and all(
                item["unchanged"]
                for item in result["protected_sources"].values()
            )
        )
    except Exception as exc:
        result["infrastructure_error"] = f"{type(exc).__name__}: {exc}"
    return result
