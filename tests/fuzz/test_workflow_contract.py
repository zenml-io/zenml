#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Contract tests for the opt-in fuzzing workflows."""

from pathlib import Path
from typing import Any, Dict, List, cast

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github" / "workflows"
PR_WORKFLOW = WORKFLOW_ROOT / "fuzz-pr.yml"
NIGHTLY_WORKFLOW = WORKFLOW_ROOT / "fuzz-nightly.yml"
CHECKOUT_ACTION = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
SETUP_PYTHON_ACTION = (
    "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
)
SETUP_UV_ACTION = "astral-sh/setup-uv@20cfd1bf945f4377ade1205e4dbc17946fc9a30d"
CACHE_ACTION = "actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9"
UPLOAD_ACTION = (
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
)
EXPECTED_ACTIONS = {
    CHECKOUT_ACTION,
    SETUP_PYTHON_ACTION,
    SETUP_UV_ACTION,
    CACHE_ACTION,
    UPLOAD_ACTION,
}
EXPECTED_MATRIX = [
    {"suite": "filters", "backend": "sqlite"},
    {"suite": "filters", "backend": "mysql"},
    {"suite": "api", "backend": "sqlite"},
    {"suite": "api", "backend": "mysql"},
    {"suite": "cli", "backend": "none"},
]
PR_CONCURRENCY = (
    "fuzz-pr-${{ github.event.pull_request.number }}-${{ "
    "((github.event.action == 'labeled' || github.event.action == 'unlabeled') "
    "&& github.event.label.name != 'run-fuzz') && github.run_id || 'active' }}"
)
PR_JOB_GATE = (
    "github.event.action != 'unlabeled' && "
    "contains(github.event.pull_request.labels.*.name, 'run-fuzz') && "
    "(github.event.action != 'labeled' || "
    "github.event.label.name == 'run-fuzz')"
)


def _load_workflow(path: Path) -> Dict[str, Any]:
    """Load a workflow without YAML 1.1 boolean coercion.

    Args:
        path: Workflow file to load.

    Returns:
        Parsed workflow mapping.
    """
    # BaseLoader constructs strings only and preserves workflow keys like `on`.
    loaded = yaml.load(  # nosec B506
        path.read_text(), Loader=yaml.BaseLoader
    )
    assert isinstance(loaded, dict)
    return cast(Dict[str, Any], loaded)


def _matrix(workflow: Dict[str, Any], job_name: str) -> List[Dict[str, str]]:
    """Extract a workflow job's concrete matrix rows.

    Args:
        workflow: Parsed workflow.
        job_name: Job containing the matrix.

    Returns:
        Concrete suite/backend combinations.
    """
    return cast(
        List[Dict[str, str]],
        workflow["jobs"][job_name]["strategy"]["matrix"]["include"],
    )


def _steps_using_actions(workflow: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract every action step in a workflow.

    Args:
        workflow: Parsed workflow.

    Returns:
        Steps that invoke external actions.
    """
    return [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "uses" in step
    ]


def test_pr_event_gate_and_concurrency_contract() -> None:
    """PR events preserve opt-in execution and cancellation behavior."""
    workflow = _load_workflow(PR_WORKFLOW)
    pull_request = workflow["on"]["pull_request"]

    assert pull_request["branches"] == ["develop"]
    assert pull_request["types"] == [
        "labeled",
        "unlabeled",
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    ]
    assert workflow["concurrency"] == {
        "group": PR_CONCURRENCY,
        "cancel-in-progress": "true",
    }
    assert " ".join(workflow["jobs"]["fuzz"]["if"].split()) == PR_JOB_GATE


@pytest.mark.parametrize(
    ("path", "job_name"),
    [(PR_WORKFLOW, "fuzz"), (NIGHTLY_WORKFLOW, "fuzz")],
)
def test_matrix_install_run_and_artifact_contract(
    path: Path, job_name: str
) -> None:
    """Both workflows use the bounded matrix and shared runner contract.

    Args:
        path: Workflow file under test.
        job_name: Matrix job to inspect.
    """
    workflow = _load_workflow(path)
    job = workflow["jobs"][job_name]

    assert job["strategy"]["fail-fast"] == "false"
    assert job["strategy"]["max-parallel"] == "2"
    assert _matrix(workflow, job_name) == EXPECTED_MATRIX
    assert job["env"]["FUZZ_PROFILE"] == (
        "pr" if path == PR_WORKFLOW else "nightly"
    )
    assert job["services"]["mysql"]["image"] == (
        "${{ matrix.backend == 'mysql' && 'mysql:8.0' || '' }}"
    )
    checkout = next(
        step for step in job["steps"] if step.get("uses") == CHECKOUT_ACTION
    )
    assert checkout["with"]["persist-credentials"] == "false"
    commands = "\n".join(
        step.get("run", "") for step in job["steps"] if "run" in step
    )
    assert "tests/fuzz/requirements.txt" in commands
    for suite, target in {
        "api": ".[server]",
        "filters": ".[local]",
        "cli": ".",
    }.items():
        assert f"{suite}) zenml_target='{target}'" in commands
    assert '-e "${zenml_target}"' in commands
    assert "python scripts/fuzz.py" in commands
    assert '--suite "${FUZZ_SUITE}"' in commands
    assert '--backend "${FUZZ_BACKEND}"' in commands
    upload = next(
        step for step in job["steps"] if step.get("uses") == UPLOAD_ACTION
    )
    assert upload["if"] == "always()"
    assert upload["with"]["retention-days"] == "14"
    assert upload["with"]["include-hidden-files"] == "true"
    assert upload["with"]["if-no-files-found"] == "error"
    dependency_cache = next(
        step
        for step in job["steps"]
        if step.get("name") == "Restore dependency cache"
    )
    assert "${{ matrix.suite }}" in dependency_cache["with"]["key"]
    assert "${{ matrix.backend }}" not in dependency_cache["with"]["key"]
    assert "pyproject.toml" in dependency_cache["with"]["key"]
    expected_paths = ["${{ env.FUZZ_OUTPUT_DIR }}"]
    if path == NIGHTLY_WORKFLOW:
        expected_paths.append("${{ env.ZENML_FUZZ_CORPUS_DIR }}")
    assert upload["with"]["path"].splitlines() == expected_paths


def test_pr_checkout_uses_immutable_head_sha() -> None:
    """Every PR matrix row checks out the event's immutable head SHA."""
    workflow = _load_workflow(PR_WORKFLOW)
    checkout = next(
        step
        for step in workflow["jobs"]["fuzz"]["steps"]
        if step.get("uses") == CHECKOUT_ACTION
    )

    assert checkout["with"]["ref"] == (
        "${{ github.event.pull_request.head.sha }}"
    )


def test_nightly_resolves_one_ref_for_every_matrix_row() -> None:
    """Scheduled and manual jobs share one resolved source revision."""
    workflow = _load_workflow(NIGHTLY_WORKFLOW)

    assert workflow["on"]["schedule"] == [{"cron": "30 2 * * *"}]
    dispatch = workflow["on"]["workflow_dispatch"]
    assert dispatch["inputs"]["ref"]["default"] == "develop"
    assert workflow["jobs"]["resolve"]["outputs"]["sha"] == (
        "${{ steps.resolve.outputs.sha }}"
    )
    fuzz_job = workflow["jobs"]["fuzz"]
    assert fuzz_job["needs"] == "resolve"
    checkout = next(
        step
        for step in fuzz_job["steps"]
        if step.get("uses") == CHECKOUT_ACTION
    )
    assert checkout["with"]["ref"] == "${{ needs.resolve.outputs.sha }}"
    assert not workflow["concurrency"]["group"].startswith("fuzz-pr-")
    corpus_cache = next(
        step
        for step in fuzz_job["steps"]
        if step.get("name") == "Restore Hypothesis corpus"
    )
    assert corpus_cache["uses"] == CACHE_ACTION
    assert corpus_cache["with"]["path"] == ("${{ env.ZENML_FUZZ_CORPUS_DIR }}")
    assert fuzz_job["env"]["ZENML_FUZZ_CORPUS_DIR"] == (
        ".fuzz-corpus/${{ matrix.suite }}-${{ matrix.backend }}"
    )
    assert (
        "${{ matrix.suite }}-${{ matrix.backend }}"
        in (corpus_cache["with"]["key"])
    )
    assert "${{ needs.resolve.outputs.sha }}" in corpus_cache["with"]["key"]
    assert "${{ github.run_id }}" in corpus_cache["with"]["key"]
    assert (
        "${{ matrix.suite }}-${{ matrix.backend }}"
        in (corpus_cache["with"]["restore-keys"])
    )


@pytest.mark.parametrize("path", [PR_WORKFLOW, NIGHTLY_WORKFLOW])
def test_workflow_security_contract(path: Path) -> None:
    """Fuzz workflows use read-only permissions and pinned actions.

    Args:
        path: Workflow file under test.
    """
    workflow = _load_workflow(path)
    source = path.read_text()

    assert workflow["permissions"] == {"contents": "read"}
    assert "pull_request_target" not in workflow["on"]
    assert "secrets." not in source
    assert "continue-on-error" not in source
    assert "write" not in source
    assert {step["uses"] for step in _steps_using_actions(workflow)}.issubset(
        EXPECTED_ACTIONS
    )
    for step in _steps_using_actions(workflow):
        if step["uses"] == CHECKOUT_ACTION:
            assert step["with"]["persist-credentials"] == "false"
