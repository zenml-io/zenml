#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Unit tests for run utils."""

from unittest.mock import MagicMock, patch

import pytest

from zenml.enums import ExecutionStatus, StackComponentType
from zenml.utils.run_utils import (
    build_dag,
    find_all_downstream_steps,
    refresh_run_status,
)


class TestBuildDagWithDownstreamSteps:
    """Test cases for build_dag function."""

    def test_single_step_no_upstream(self):
        """Test with single step having no upstream dependencies."""
        steps = {"step1": []}
        result = build_dag(steps)

        expected = {"step1": set()}
        assert result == expected

    def test_linear_pipeline(self):
        """Test with linear pipeline: step1 -> step2 -> step3."""
        steps = {
            "step1": [],
            "step2": ["step1"],
            "step3": ["step2"],
        }
        result = build_dag(steps)

        expected = {"step1": {"step2"}, "step2": {"step3"}, "step3": set()}
        assert result == expected

    def test_diamond_pipeline(self):
        """Test with diamond-shaped pipeline: step1 -> step2,step3 -> step4."""
        steps = {
            "step1": [],
            "step2": ["step1"],
            "step3": ["step1"],
            "step4": ["step2", "step3"],
        }
        result = build_dag(steps)

        expected = {
            "step1": {"step2", "step3"},
            "step2": {"step4"},
            "step3": {"step4"},
            "step4": set(),
        }
        assert result == expected

    def test_complex_pipeline(self):
        """Test with more complex pipeline structure."""
        steps = {
            "step1": [],
            "step2": ["step1"],
            "step3": ["step1"],
            "step4": ["step2", "step3"],
            "step5": ["step2"],
            "step6": ["step4", "step5"],
        }
        result = build_dag(steps)

        expected = {
            "step1": {"step2", "step3"},
            "step2": {"step4", "step5"},
            "step3": {"step4"},
            "step4": {"step6"},
            "step5": {"step6"},
            "step6": set(),
        }
        assert result == expected


class TestFindAllDownstreamSteps:
    """Test cases for find_all_downstream_steps function."""

    def test_no_downstream_steps(self):
        """Test step with no downstream dependencies."""
        dag = {"step1": set()}
        result = find_all_downstream_steps("step1", dag)
        assert result == set()

    def test_single_downstream_step(self):
        """Test step with single downstream dependency."""
        dag = {"step1": {"step2"}, "step2": set()}
        result = find_all_downstream_steps("step1", dag)
        assert result == {"step2"}

    def test_linear_downstream_chain(self):
        """Test linear chain: step1 -> step2 -> step3 -> step4."""
        dag = {
            "step1": {"step2"},
            "step2": {"step3"},
            "step3": {"step4"},
            "step4": set(),
        }
        result = find_all_downstream_steps("step1", dag)
        assert result == {"step2", "step3", "step4"}

    def test_multiple_immediate_downstream(self):
        """Test step with multiple immediate downstream steps."""
        dag = {"step1": {"step2", "step3"}, "step2": set(), "step3": set()}
        result = find_all_downstream_steps("step1", dag)
        assert result == {"step2", "step3"}

    def test_diamond_pattern_downstream(self):
        """Test diamond pattern: step1 -> step2,step3 -> step4."""
        dag = {
            "step1": {"step2", "step3"},
            "step2": {"step4"},
            "step3": {"step4"},
            "step4": set(),
        }
        result = find_all_downstream_steps("step1", dag)
        assert result == {"step2", "step3", "step4"}

    def test_complex_downstream_tree(self):
        """Test complex downstream tree structure."""
        dag = {
            "step1": {"step2", "step3"},
            "step2": {"step4", "step5"},
            "step3": {"step6"},
            "step4": {"step7"},
            "step5": {"step7"},
            "step6": {"step8"},
            "step7": set(),
            "step8": set(),
        }
        result = find_all_downstream_steps("step1", dag)
        assert result == {
            "step2",
            "step3",
            "step4",
            "step5",
            "step6",
            "step7",
            "step8",
        }

    def test_middle_step_downstream(self):
        """Test finding downstream steps from middle of pipeline."""
        dag = {
            "step1": {"step2"},
            "step2": {"step3", "step4"},
            "step3": {"step5"},
            "step4": {"step5"},
            "step5": set(),
        }
        result = find_all_downstream_steps("step2", dag)
        assert result == {"step3", "step4", "step5"}

    def test_step_not_in_dag(self):
        """Test with step name not in reverse DAG (should raise KeyError)."""
        dag = {"step1": {"step2"}, "step2": set()}

        with pytest.raises(KeyError):
            find_all_downstream_steps("nonexistent_step", dag)


def _refresh_with_orchestrator_status(
    run_status: ExecutionStatus, orchestrator_status: ExecutionStatus
) -> MagicMock:
    """Refresh a run whose orchestrator reports a status, return the store."""
    run = MagicMock(status=run_status)
    run.stack.components = {StackComponentType.ORCHESTRATOR: [MagicMock()]}
    orchestrator = MagicMock()
    orchestrator.fetch_status.return_value = (orchestrator_status, {})
    zen_store = MagicMock()

    with patch(
        "zenml.utils.run_utils.StackComponent.from_model",
        return_value=orchestrator,
    ):
        refresh_run_status(run=run, zen_store=zen_store)

    return zen_store


@pytest.mark.parametrize(
    "orchestrator_status",
    [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED],
)
def test_refresh_keeps_paused_run_paused(orchestrator_status):
    """A paused run's exited orchestrator process must not finish the run."""
    zen_store = _refresh_with_orchestrator_status(
        run_status=ExecutionStatus.PAUSED,
        orchestrator_status=orchestrator_status,
    )

    zen_store.update_run.assert_not_called()


def test_refresh_updates_running_run():
    """A running run takes the status reported by its orchestrator."""
    zen_store = _refresh_with_orchestrator_status(
        run_status=ExecutionStatus.RUNNING,
        orchestrator_status=ExecutionStatus.COMPLETED,
    )

    zen_store.update_run.assert_called_once()
    assert (
        zen_store.update_run.call_args.kwargs["run_update"].status
        == ExecutionStatus.COMPLETED
    )
