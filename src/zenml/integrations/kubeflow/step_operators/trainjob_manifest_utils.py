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
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, Union

from zenml.config.resource_settings import ResourceSettings
from zenml.logger import get_logger

logger = get_logger(__name__)

TRAINJOB_GROUP = "trainer.kubeflow.org"
TRAINJOB_VERSION = "v1alpha1"
TRAINJOB_PLURAL = "trainjobs"

_MEMORY_UNIT_TO_K8S = {
    "KiB": "Ki",
    "MiB": "Mi",
    "GiB": "Gi",
    "TiB": "Ti",
    "PiB": "Pi",
    "KB": "K",
    "MB": "M",
    "GB": "G",
    "TB": "T",
    "PB": "P",
}
NUM_PROC_PER_NODE_AUTO_VALUES = {"auto", "cpu", "gpu"}


def _format_cpu_count(cpu_count: float) -> str:
    """Formats CPU counts for Kubernetes resource quantities.

    Args:
        cpu_count: CPU count from `ResourceSettings`.

    Returns:
        A Kubernetes-compatible CPU quantity.
    """
    if float(cpu_count).is_integer():
        return str(int(cpu_count))
    return str(cpu_count)


def _memory_to_kubernetes_quantity(memory: str) -> str:
    """Converts ZenML memory values to Kubernetes memory quantities.

    Args:
        memory: The memory value from `ResourceSettings`.

    Returns:
        Kubernetes memory quantity string.
    """
    for source_unit, target_unit in _MEMORY_UNIT_TO_K8S.items():
        if memory.endswith(source_unit):
            return memory[: -len(source_unit)] + target_unit
    return memory


def _deep_merge_dicts(
    base: Dict[str, Any], override: Mapping[str, Any]
) -> Dict[str, Any]:
    """Deep merges override into a base dict.

    Args:
        base: Base dict.
        override: Dict values to merge.

    Returns:
        The merged dict.
    """
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and key in base
            and isinstance(base[key], dict)
        ):
            base[key] = _deep_merge_dicts(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _normalize_num_proc_per_node(
    value: Union[int, str],
) -> Union[int, Literal["auto", "cpu", "gpu"]]:
    """Normalizes and validates Trainer `numProcPerNode`.

    Args:
        value: Raw value.

    Returns:
        Normalized value.

    Raises:
        ValueError: If the value is invalid.
    """
    if isinstance(value, bool):
        raise ValueError(
            "`num_proc_per_node` must be an integer >= 1 or one of "
            "`auto`, `cpu`, `gpu`."
        )

    if isinstance(value, int):
        if value < 1:
            raise ValueError("`num_proc_per_node` must be greater than 0.")
        return value

    if not isinstance(value, str):
        raise ValueError(
            "`num_proc_per_node` must be an integer >= 1 or one of "
            "`auto`, `cpu`, `gpu`."
        )

    normalized = value.strip().lower()
    if normalized in NUM_PROC_PER_NODE_AUTO_VALUES:
        return normalized

    if normalized.isdigit():
        parsed = int(normalized)
        if parsed < 1:
            raise ValueError("`num_proc_per_node` must be greater than 0.")
        return parsed

    raise ValueError(
        "`num_proc_per_node` must be an integer >= 1 or one of "
        "`auto`, `cpu`, `gpu`."
    )


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
        cpu_value = _format_cpu_count(resource_settings.cpu_count)
        requests["cpu"] = cpu_value
        limits["cpu"] = cpu_value

    if resource_settings.memory is not None:
        memory_value = _memory_to_kubernetes_quantity(resource_settings.memory)
        requests["memory"] = memory_value
        limits["memory"] = memory_value

    if (
        resource_settings.gpu_count is not None
        and resource_settings.gpu_count > 0
    ):
        # TODO: Use correct value from resource settings
        # gpu_value = str(resource_settings.gpu_count)
        requests["nvidia.com/gpu"] = 1
        limits["nvidia.com/gpu"] = 1

    if not requests and not limits:
        return {}

    return {"requests": requests, "limits": limits}


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
        num_proc_per_node: Optional trainer `numProcPerNode` value.
        resource_settings: Step resource settings.
        environment: Environment variables inherited from the launcher process.
        trainer_env: Additional trainer-specific environment variables.
        trainer_overrides: Optional additional `spec.trainer` fields.
        pod_template_overrides: Optional `spec.podTemplateOverrides`.
        labels: Optional metadata labels.
        annotations: Optional metadata annotations.

    Returns:
        A Kubernetes custom object manifest for a Trainer v2 TrainJob.
    """
    combined_environment = dict(environment)
    combined_environment.update(trainer_env)
    env_entries = [
        {"name": key, "value": value}
        for key, value in sorted(combined_environment.items())
    ]

    trainer_spec: Dict[str, Any] = {
        "numNodes": num_nodes,
        "image": image,
        "command": command,
        "args": args,
    }

    if num_proc_per_node is not None:
        trainer_spec["numProcPerNode"] = _normalize_num_proc_per_node(
            num_proc_per_node
        )

    if env_entries:
        trainer_spec["env"] = env_entries

    resources_per_node = build_resources_per_node(resource_settings)
    if resources_per_node:
        trainer_spec["resourcesPerNode"] = resources_per_node

    if trainer_overrides:
        trainer_spec = _deep_merge_dicts(
            base=trainer_spec, override=trainer_overrides
        )

    if "numProcPerNode" in trainer_spec:
        trainer_spec["numProcPerNode"] = _normalize_num_proc_per_node(
            trainer_spec["numProcPerNode"]
        )

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

    metadata: Dict[str, Any] = {"name": trainjob_name}
    if labels:
        metadata["labels"] = dict(labels)
    if annotations:
        metadata["annotations"] = dict(annotations)

    return {
        "apiVersion": f"{TRAINJOB_GROUP}/{TRAINJOB_VERSION}",
        "kind": "TrainJob",
        "metadata": metadata,
        "spec": spec,
    }
