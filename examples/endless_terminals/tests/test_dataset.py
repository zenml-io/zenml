"""Qualification checks distinguish invalid output from broken verification."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import dataset
import pytest

Qualification = tuple[
    dict[str, Any], Path, list[dict[str, Any]], MagicMock, MagicMock
]


def grade(valid: bool) -> dict[str, Any]:
    """Build a verifier outcome for qualification tests.

    Args:
        valid: Whether the final state passes its verifier.

    Returns:
        A complete mocked verifier result.
    """
    return {
        "raw_reward": int(valid),
        "audited_valid": valid,
        "infrastructure_error": None,
        "protected_sources": {},
        "test_counts": {
            "total": 2,
            "failure": int(not valid),
            "error": 0,
            "skipped": 0,
        },
    }


@pytest.fixture
def qualification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Qualification:
    """Provide four isolated mock environments and their grading results.

    Args:
        tmp_path: Temporary task directory.
        monkeypatch: Scoped patch helper.

    Returns:
        Task, directory, grading results, environment constructor, and verifier.
    """
    solution = tmp_path / "solution"
    solution.mkdir()
    (solution / "solve.sh").write_text("echo reference")
    environments = [MagicMock() for _ in range(4)]
    for env in environments:
        env.__enter__.return_value = env
        env.execute.return_value = (True, "")
    constructor = MagicMock(side_effect=environments)
    monkeypatch.setattr(dataset, "DockerEnvironment", constructor)
    grades = [grade(True), grade(False), grade(True), grade(False)]
    verifier = MagicMock(side_effect=grades)
    monkeypatch.setattr(dataset, "grade_environment", verifier)
    task = {
        "task_id": "task-a",
        "local_image_id": "image-id",
        "corrupted_output_probe": "/home/user/report.txt",
    }
    return task, tmp_path, grades, constructor, verifier


def test_qualification_requires_corrupted_output_rejection(
    qualification: Qualification,
) -> None:
    """Use a fresh reference-plus-corruption environment after reference success.

    Args:
        qualification: Mock qualification fixture.
    """
    task, directory, _, constructor, verifier = qualification
    results = dataset.qualify_task(task, directory)
    assert list(results) == ["initial", "noop", "reference", "corrupted"]
    assert constructor.call_count == 4
    corrupt_env = verifier.call_args_list[-1].args[0]
    commands = [call.args[0] for call in corrupt_env.execute.call_args_list]
    assert commands == [
        "echo reference",
        "printf 'INVALID_OUTPUT\\n' > /home/user/report.txt",
    ]
    corrupt_env.__exit__.assert_called_once()


@pytest.mark.parametrize("phase", [1, 3])
@pytest.mark.parametrize(
    "defect", ["error", "skipped", "no_failure", "accepted", "source_mutation"]
)
def test_rejects_invalid_negative_probe(
    qualification: Qualification, phase: int, defect: str
) -> None:
    """Reject accepted corruption and verifier failures that are not assertions.

    Args:
        qualification: Mock qualification fixture.
        phase: Negative qualification phase index.
        defect: Verifier outcome that must invalidate qualification.
    """
    task, directory, grades, _, _ = qualification
    if defect in ("error", "skipped"):
        grades[phase]["test_counts"][defect] = 1
    elif defect == "no_failure":
        grades[phase]["test_counts"]["failure"] = 0
    elif defect == "source_mutation":
        grades[phase]["protected_sources"] = {"source": {"unchanged": False}}
    else:
        grades[phase].update(raw_reward=1, audited_valid=True)
    with pytest.raises(RuntimeError):
        dataset.qualify_task(task, directory)


def test_rejects_missing_corruption_probe(
    qualification: Qualification,
) -> None:
    """Fail before containers start when the reviewed probe is absent.

    Args:
        qualification: Mock qualification fixture.
    """
    task, directory, _, constructor, _ = qualification
    task.pop("corrupted_output_probe")
    with pytest.raises(RuntimeError, match="corruption probe"):
        dataset.qualify_task(task, directory)
    constructor.assert_not_called()
