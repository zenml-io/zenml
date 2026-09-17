#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License")
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
"""Unit tests for DAG generation utilities."""

from typing import List

from zenml.config.step_configurations import StepSpec
from zenml.zen_stores.dag.models import DAGStepView
from zenml.zen_stores.dag.utils import sort_dag_steps


def _step_with_upstream_steps(upstream_steps: List[str]) -> DAGStepView:
    """Create a DAG step view with upstream steps."""
    return DAGStepView.model_construct(
        spec=StepSpec.model_construct(upstream_steps=upstream_steps)
    )


def test_sort_dag_steps_uses_dependency_order() -> None:
    """DAG steps are sorted independently of their input order."""
    steps = {
        "downstream": _step_with_upstream_steps(["upstream"]),
        "upstream": _step_with_upstream_steps([]),
    }

    sorted_steps = sort_dag_steps(steps)

    assert [name for name, _ in sorted_steps] == ["upstream", "downstream"]
