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

from unittest.mock import Mock

import pytest

from zenml.zen_stores.schemas.pipeline_run_schemas import (
    build_dag_with_downstream_steps,
    find_all_downstream_steps,
)


class TestBuildDagWithDownstreamSteps:
    """Test cases for build_dag_with_downstream_steps function."""

    def test_empty_steps_list(self):
        """Test with empty steps list."""
        steps = []
        result = build_dag_with_downstream_steps(steps)
        assert result == {}

    def test_single_step_no_upstream(self):
        """Test with single step having no upstream dependencies."""
        # Mock step with no upstream dependencies
        step = Mock()
        step.config.name = "step1"
        step.spec.upstream_steps = []

        result = build_dag_with_downstream_steps([step])

        expected = {"step1": set()}
        assert result == expected

    def test_linear_pipeline(self):
        """Test with linear pipeline: step1 -> step2 -> step3."""
        # Create mock steps
        step1 = Mock()
        step1.config.name = "step1"
        step1.spec.upstream_steps = []

        step2 = Mock()
        step2.config.name = "step2"
        step2.spec.upstream_steps = ["step1"]

        step3 = Mock()
        step3.config.name = "step3"
        step3.spec.upstream_steps = ["step2"]

        result = build_dag_with_downstream_steps([step1, step2, step3])

        expected = {"step1": {"step2"}, "step2": {"step3"}, "step3": set()}
        assert result == expected

    def test_diamond_pipeline(self):
        """Test with diamond-shaped pipeline: step1 -> step2,step3 -> step4."""
        # Create mock steps
        step1 = Mock()
        step1.config.name = "step1"
        step1.spec.upstream_steps = []

        step2 = Mock()
        step2.config.name = "step2"
        step2.spec.upstream_steps = ["step1"]

        step3 = Mock()
        step3.config.name = "step3"
        step3.spec.upstream_steps = ["step1"]

        step4 = Mock()
        step4.config.name = "step4"
        step4.spec.upstream_steps = ["step2", "step3"]

        steps = [step1, step2, step3, step4]
        result = build_dag_with_downstream_steps(steps)

        expected = {
            "step1": {"step2", "step3"},
            "step2": {"step4"},
            "step3": {"step4"},
            "step4": set(),
        }
        assert result == expected

    def test_complex_pipeline(self):
        """Test with more complex pipeline structure."""
        # Create mock steps for a complex DAG
        steps_data = [
            ("step1", []),
            ("step2", ["step1"]),
            ("step3", ["step1"]),
            ("step4", ["step2", "step3"]),
            ("step5", ["step2"]),
            ("step6", ["step4", "step5"]),
        ]

        steps = []
        for name, upstream in steps_data:
            step = Mock()
            step.config.name = name
            step.spec.upstream_steps = upstream
            steps.append(step)

        result = build_dag_with_downstream_steps(steps)

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
