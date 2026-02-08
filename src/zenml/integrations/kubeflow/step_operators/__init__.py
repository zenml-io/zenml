#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Kubeflow integration step operators."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from zenml.integrations.kubeflow.step_operators.kubeflow_trainer_step_operator import (  # noqa: F401
        KubeflowTrainerStepOperator,
    )


def __getattr__(name: str) -> Any:
    """Lazily imports step operator classes."""
    if name == "KubeflowTrainerStepOperator":
        from zenml.integrations.kubeflow.step_operators.kubeflow_trainer_step_operator import (  # noqa: E501
            KubeflowTrainerStepOperator,
        )

        return KubeflowTrainerStepOperator
    raise AttributeError(
        f"module `{__name__}` has no attribute `{name}`."
    )

__all__ = ["KubeflowTrainerStepOperator"]
