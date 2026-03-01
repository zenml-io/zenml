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
"""Utilities for building Kubeflow Trainer v2 TrainJob manifests."""

import copy
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from zenml.config.resource_settings import ResourceSettings
from zenml.integrations.kubeflow.step_operators.trainjob_value_utils import (
    deep_merge_dicts,
    format_cpu_count,
    memory_to_kubernetes_quantity,
    normalize_num_proc_per_node,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

TRAINJOB_GROUP = "trainer.kubeflow.org"
TRAINJOB_VERSION = "v1alpha1"
TRAINJOB_PLURAL = "trainjobs"


def build_resources_per_node(
    resource_settings: ResourceSettings,
) -> Dict[str, Dict[str, str]]:
    """Builds resourcesPerNode for Trainer v2 manifests.

    Args:
        resource_settings: Step resource settings.

    Returns:
        A Kubernetes resources dict suitable for `resourcesPerNode`.
    """
    requests: Dict[str, str] = {}
    limits: Dict[str, str] = {}

    if resource_settings.cpu_count is not None:
        cpu_value = format_cpu_count(resource_settings.cpu_count)
        requests["cpu"] = cpu_value
        limits["cpu"] = cpu_value

    if resource_settings.memory is not None:
        memory_value = memory_to_kubernetes_quantity(resource_settings.memory)
        requests["memory"] = memory_value
        limits["memory"] = memory_value

    if (
        resource_settings.gpu_count is not None
        and resource_settings.gpu_count > 0
    ):
        gpu_value = str(resource_settings.gpu_count)
        requests["nvidia.com/gpu"] = gpu_value
        limits["nvidia.com/gpu"] = gpu_value

    if not requests and not limits:
        return {}

    return {"requests": requests, "limits": limits}


def _build_env_entries(
    environment: Mapping[str, str],
    trainer_env: Mapping[str, str],
) -> List[Dict[str, str]]:
    """Builds a deterministic trainer environment list."""
    combined_environment = dict(environment)
    combined_environment.update(trainer_env)
    return [
        {"name": key, "value": value}
        for key, value in sorted(combined_environment.items())
    ]


def _flatten_multi_proc_trainer_spec(trainer_spec: Dict[str, Any]) -> None:
    """Flattens a multi-process setup to one process per Trainer pod."""
    # Each ZenML Trainer pod runs exactly one process — there is no
    # torchrun wrapper to spawn extra workers inside a pod.  When the
    # user requests numProcPerNode > 1, the intent is to have that many
    # total GPU workers.  We flatten the request so the controller
    # creates one pod per worker: numNodes = nodes × procsPerNode,
    # numProcPerNode = 1.
    effective_num_nodes = trainer_spec.get("numNodes", 1)
    effective_nproc = trainer_spec.get("numProcPerNode")
    if isinstance(effective_nproc, int) and effective_nproc > 1:
        total_workers = effective_num_nodes * effective_nproc
        logger.info(
            "Flattening distributed request: numNodes=%d × "
            "numProcPerNode=%d → numNodes=%d, numProcPerNode=1. "
            "Each pod runs one process; Kubernetes scheduling "
            "distributes pods across physical nodes.",
            effective_num_nodes,
            effective_nproc,
            total_workers,
        )
        trainer_spec["numNodes"] = total_workers
        trainer_spec["numProcPerNode"] = 1

        rpn = trainer_spec.get("resourcesPerNode") or {}
        gpu_request = (rpn.get("requests") or {}).get("nvidia.com/gpu")
        if gpu_request:
            logger.warning(
                "After flattening, each of the %d pods requests %s "
                "GPU(s) (total: %d GPUs). If gpu_count should be the "
                "total across all workers, set gpu_count=%d and "
                "num_proc_per_node=1 instead.",
                total_workers,
                gpu_request,
                total_workers * int(gpu_request),
                int(gpu_request),
            )
    elif (
        effective_num_nodes is not None
        and effective_num_nodes > 1
        and effective_nproc is not None
        and not isinstance(effective_nproc, int)
    ):
        logger.warning(
            "numNodes=%d with non-integer numProcPerNode=%r: the "
            "Kubeflow Trainer v2 controller may not propagate "
            "numNodes correctly. Multi-node training might not work "
            "as expected.",
            effective_num_nodes,
            effective_nproc,
        )


def _build_trainer_spec(
    num_nodes: int,
    image: str,
    command: List[str],
    args: List[str],
    resource_settings: ResourceSettings,
    environment: Mapping[str, str],
    trainer_env: Mapping[str, str],
    num_proc_per_node: Optional[Union[int, str]],
    trainer_overrides: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Builds the `spec.trainer` section for a TrainJob manifest."""
    trainer_spec: Dict[str, Any] = {
        "numNodes": num_nodes,
        "image": image,
        "command": command,
        "args": args,
    }

    if num_proc_per_node is not None:
        trainer_spec["numProcPerNode"] = normalize_num_proc_per_node(
            num_proc_per_node
        )

    env_entries = _build_env_entries(environment, trainer_env)
    if env_entries:
        trainer_spec["env"] = env_entries

    resources_per_node = build_resources_per_node(resource_settings)
    if resources_per_node:
        trainer_spec["resourcesPerNode"] = resources_per_node

    if trainer_overrides:
        trainer_spec = deep_merge_dicts(
            base=trainer_spec, override=trainer_overrides
        )

    if "numProcPerNode" in trainer_spec:
        trainer_spec["numProcPerNode"] = normalize_num_proc_per_node(
            trainer_spec["numProcPerNode"]
        )

    _flatten_multi_proc_trainer_spec(trainer_spec)
    return trainer_spec


def _build_trainjob_spec(
    runtime_ref_name: str,
    runtime_ref_kind: str,
    runtime_ref_api_group: str,
    trainer_spec: Dict[str, Any],
    pod_template_overrides: Optional[Sequence[Mapping[str, Any]]],
) -> Dict[str, Any]:
    """Builds the top-level TrainJob `spec` section."""
    spec: Dict[str, Any] = {
        "runtimeRef": {
            "name": runtime_ref_name,
            "kind": runtime_ref_kind,
            "apiGroup": runtime_ref_api_group,
        },
        "trainer": trainer_spec,
    }
    if pod_template_overrides:
        spec["podTemplateOverrides"] = copy.deepcopy(
            list(pod_template_overrides)
        )
    return spec


def _build_trainjob_metadata(
    trainjob_name: str,
    labels: Optional[Mapping[str, str]],
    annotations: Optional[Mapping[str, str]],
) -> Dict[str, Any]:
    """Builds the top-level TrainJob metadata section."""
    metadata: Dict[str, Any] = {"name": trainjob_name}
    if labels:
        metadata["labels"] = dict(labels)
    if annotations:
        metadata["annotations"] = dict(annotations)
    return metadata


def build_trainjob_manifest(
    trainjob_name: str,
    image: str,
    command: List[str],
    args: List[str],
    runtime_ref_name: str,
    runtime_ref_kind: str,
    runtime_ref_api_group: str,
    num_nodes: int,
    resource_settings: ResourceSettings,
    environment: Mapping[str, str],
    trainer_env: Mapping[str, str],
    num_proc_per_node: Optional[Union[int, str]] = None,
    trainer_overrides: Optional[Mapping[str, Any]] = None,
    pod_template_overrides: Optional[Sequence[Mapping[str, Any]]] = None,
    labels: Optional[Mapping[str, str]] = None,
    annotations: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Builds a Kubeflow Trainer v2 TrainJob manifest.

    Args:
        trainjob_name: Name of the TrainJob.
        image: Image to run.
        command: Command to execute.
        args: Command args to execute.
        runtime_ref_name: Runtime reference name.
        runtime_ref_kind: Runtime reference kind.
        runtime_ref_api_group: Runtime reference api group.
        num_nodes: Number of trainer nodes.
        resource_settings: Step resource settings.
        environment: Environment variables inherited from the launcher process.
        trainer_env: Additional trainer-specific environment variables.
        num_proc_per_node: Optional trainer `numProcPerNode` value.
        trainer_overrides: Optional additional `spec.trainer` fields.
        pod_template_overrides: Optional `spec.podTemplateOverrides`.
        labels: Optional metadata labels.
        annotations: Optional metadata annotations.

    Returns:
        A Kubernetes custom object manifest for a Trainer v2 TrainJob.
    """
    trainer_spec = _build_trainer_spec(
        num_nodes=num_nodes,
        image=image,
        command=command,
        args=args,
        resource_settings=resource_settings,
        environment=environment,
        trainer_env=trainer_env,
        num_proc_per_node=num_proc_per_node,
        trainer_overrides=trainer_overrides,
    )
    spec = _build_trainjob_spec(
        runtime_ref_name=runtime_ref_name,
        runtime_ref_kind=runtime_ref_kind,
        runtime_ref_api_group=runtime_ref_api_group,
        trainer_spec=trainer_spec,
        pod_template_overrides=pod_template_overrides,
    )
    metadata = _build_trainjob_metadata(
        trainjob_name=trainjob_name,
        labels=labels,
        annotations=annotations,
    )

    return {
        "apiVersion": f"{TRAINJOB_GROUP}/{TRAINJOB_VERSION}",
        "kind": "TrainJob",
        "metadata": metadata,
        "spec": spec,
    }
