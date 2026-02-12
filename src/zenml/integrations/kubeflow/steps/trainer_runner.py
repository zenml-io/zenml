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
"""Decorator utilities for Kubeflow Trainer step operator usage."""

import copy
from typing import Any, Callable, Dict, List, Literal, Optional, Union

from zenml import get_pipeline_context
from zenml.integrations.kubeflow import KUBEFLOW_TRAINER_STEP_OPERATOR_FLAVOR
from zenml.integrations.kubeflow.flavors import (
    KubeflowTrainerStepOperatorSettings,
)
from zenml.logger import get_logger
from zenml.steps import BaseStep

logger = get_logger(__name__)


def _deep_merge_dicts(
    base: Dict[str, Any], override: Dict[str, Any]
) -> Dict[str, Any]:
    """Deep merges override values into a base dict.

    Args:
        base: Base dictionary.
        override: Dictionary values to merge.

    Returns:
        Merged dictionary.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and key in merged
            and isinstance(merged[key], dict)
        ):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def run_with_trainer(
    step_function_top_level: Optional[BaseStep] = None,
    *,
    runtime_ref_name: str,
    runtime_ref_kind: str = "ClusterTrainingRuntime",
    runtime_ref_api_group: str = "trainer.kubeflow.org",
    num_nodes: int = 1,
    num_proc_per_node: Optional[
        Union[int, Literal["auto", "cpu", "gpu"]]
    ] = None,
    trainer_overrides: Optional[Dict[str, Any]] = None,
    trainer_env: Optional[Dict[str, str]] = None,
    pod_template_overrides: Optional[List[Dict[str, Any]]] = None,
    ml_policy: Optional[Dict[str, Any]] = None,
    pod_template_override: Optional[Dict[str, Any]] = None,
    poll_interval_seconds: float = 5.0,
    timeout_seconds: Optional[int] = None,
    delete_trainjob_after_completion: bool = False,
    kubernetes_namespace: str = "default",
    incluster: bool = False,
    kubernetes_context: Optional[str] = None,
    image: Optional[str] = None,
) -> Union[Callable[[BaseStep], BaseStep], BaseStep]:
    """Configures a step to run through the Kubeflow Trainer step operator.

    The decorator enables step-operator execution and injects
    `KubeflowTrainerStepOperatorSettings` as step-operator settings.

    Args:
        step_function_top_level: Optional step to wrap in functional mode.
        runtime_ref_name: Name of the Trainer runtime reference.
        runtime_ref_kind: Runtime kind for the runtime reference.
        runtime_ref_api_group: API group for the runtime reference.
        num_nodes: Number of trainer nodes.
        num_proc_per_node: Optional trainer `numProcPerNode` value.
        trainer_overrides: Optional additional fields merged into
            `spec.trainer`.
        trainer_env: Additional environment variables for trainer replicas.
        pod_template_overrides: Optional `spec.podTemplateOverrides`.
        ml_policy: Deprecated alias for trainer field overrides.
        pod_template_override: Deprecated alias for trainer field overrides.
        poll_interval_seconds: TrainJob polling interval.
        timeout_seconds: Optional timeout while waiting for TrainJob terminal
            status.
        delete_trainjob_after_completion: Whether to delete the TrainJob when
            it reaches a terminal state.
        kubernetes_namespace: Namespace where the TrainJob is created.
        incluster: Whether to use in-cluster Kubernetes client configuration.
        kubernetes_context: Kubernetes context when not using in-cluster
            config.
        image: Optional image to use for trainer replicas.

    Returns:
        The configured step.
    """
    if num_nodes < 1:
        raise ValueError("`num_nodes` must be greater than or equal to 1.")
    if poll_interval_seconds <= 0:
        raise ValueError("`poll_interval_seconds` must be greater than 0.")
    if timeout_seconds is not None and timeout_seconds <= 0:
        raise ValueError("`timeout_seconds` must be greater than 0.")

    effective_trainer_overrides = dict(trainer_overrides or {})
    if ml_policy:
        logger.warning(
            "`ml_policy` is deprecated; use `num_proc_per_node` and "
            "`trainer_overrides` instead."
        )
        effective_trainer_overrides = _deep_merge_dicts(
            effective_trainer_overrides, dict(ml_policy)
        )
    if pod_template_override:
        logger.warning(
            "`pod_template_override` is deprecated; use "
            "`trainer_overrides` for trainer fields and "
            "`pod_template_overrides` for TrainJob pod template overrides."
        )
        effective_trainer_overrides = _deep_merge_dicts(
            effective_trainer_overrides, dict(pod_template_override)
        )

    effective_num_proc_per_node = num_proc_per_node
    if (
        effective_num_proc_per_node is None
        and "numProcPerNode" in effective_trainer_overrides
    ):
        effective_num_proc_per_node = effective_trainer_overrides.pop(
            "numProcPerNode"
        )

    effective_pod_template_overrides = list(pod_template_overrides or [])
    if (
        not effective_pod_template_overrides
        and "podTemplateOverrides" in effective_trainer_overrides
    ):
        extracted_overrides = effective_trainer_overrides.pop(
            "podTemplateOverrides"
        )
        if isinstance(extracted_overrides, list):
            effective_pod_template_overrides = extracted_overrides
        elif isinstance(extracted_overrides, dict):
            effective_pod_template_overrides = [extracted_overrides]

    settings = KubeflowTrainerStepOperatorSettings(
        runtime_ref_name=runtime_ref_name,
        runtime_ref_kind=runtime_ref_kind,
        runtime_ref_api_group=runtime_ref_api_group,
        num_nodes=num_nodes,
        num_proc_per_node=effective_num_proc_per_node,
        trainer_overrides=effective_trainer_overrides,
        trainer_env=dict(trainer_env or {}),
        pod_template_overrides=effective_pod_template_overrides,
        poll_interval_seconds=poll_interval_seconds,
        timeout_seconds=timeout_seconds,
        delete_trainjob_after_completion=delete_trainjob_after_completion,
        kubernetes_namespace=kubernetes_namespace,
        incluster=incluster,
        kubernetes_context=kubernetes_context,
        image=image,
    )

    def _decorator(step_function: BaseStep) -> BaseStep:
        try:
            get_pipeline_context()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                f"`{run_with_trainer.__name__}` decorator cannot be used "
                "in a functional way with steps, please apply decoration "
                "directly to a step instead.\n"
                "Example (allowed):\n"
                f"@{run_with_trainer.__name__}(...)\n"
                f"def {step_function.name}(...):\n"
                "    ...\n"
                "Example (not allowed):\n"
                "def my_pipeline(...):\n"
                f"    {run_with_trainer.__name__}({step_function.name}, ...)(...)\n"
            )

        configured_step_operator = (
            step_function.configuration.step_operator
            or KUBEFLOW_TRAINER_STEP_OPERATOR_FLAVOR
        )

        return step_function.configure(
            step_operator=configured_step_operator,
            settings={"step_operator": settings},
            merge=True,
        )

    if step_function_top_level is not None:
        return _decorator(step_function_top_level)
    return _decorator
