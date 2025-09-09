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

import pytest

from zenml.utils.run_utils import (
    build_dag,
    find_all_downstream_steps,
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
