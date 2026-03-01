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
"""Value-level utilities for Kubeflow Trainer TrainJob manifest generation."""

import copy
from typing import Any, Dict, Literal, Mapping, Optional, Union

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
_NUM_PROC_PER_NODE_AUTO_VALUES = {"auto", "cpu", "gpu"}


def format_cpu_count(cpu_count: float) -> str:
    """Formats CPU counts for Kubernetes resource quantities.

    Args:
        cpu_count: CPU count from `ResourceSettings`.

    Returns:
        A Kubernetes-compatible CPU quantity.
    """
    if float(cpu_count).is_integer():
        return str(int(cpu_count))
    return str(cpu_count)


def memory_to_kubernetes_quantity(memory: str) -> str:
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


def deep_merge_dicts(
    base: Dict[str, Any], override: Mapping[str, Any]
) -> Dict[str, Any]:
    """Deep merges override values into a base dict without mutation.

    Args:
        base: Base dict (not modified).
        override: Dict values to merge on top.

    Returns:
        A new merged dict.
    """
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if (
            isinstance(value, dict)
            and key in merged
            and isinstance(merged[key], dict)
        ):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def normalize_num_proc_per_node(
    value: Union[int, str, None],
) -> Optional[Union[int, Literal["auto", "cpu", "gpu"]]]:
    """Normalizes and validates Trainer `numProcPerNode`.

    Args:
        value: Raw value — an integer >= 1, one of ``auto``/``cpu``/``gpu``,
            or ``None`` to leave unset.

    Returns:
        Normalized value, or ``None`` when the input is ``None``.

    Raises:
        ValueError: If the value is invalid.
    """
    if value is None:
        return None

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
    if normalized in _NUM_PROC_PER_NODE_AUTO_VALUES:
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
