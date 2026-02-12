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
"""Distributed rank detection utilities for Kubeflow Trainer replicas."""

import os
from typing import Mapping, MutableMapping, Optional, Sequence

_GLOBAL_RANK_KEYS = (
    "RANK",
    "TRAINER_GLOBAL_RANK",
    "TRAINER_RANK",
    "OMPI_COMM_WORLD_RANK",
    "PMI_RANK",
    "SLURM_PROCID",
)
_LOCAL_RANK_KEYS = ("LOCAL_RANK", "MPI_LOCALRANKID")
_WORLD_SIZE_KEYS = (
    "WORLD_SIZE",
    "TRAINER_WORLD_SIZE",
    "OMPI_COMM_WORLD_SIZE",
    "PMI_SIZE",
    "SLURM_NTASKS",
)


def _read_first_int(
    keys: Sequence[str], environment: Mapping[str, str]
) -> Optional[int]:
    """Reads the first parseable integer for one of the provided keys.

    Args:
        keys: Candidate environment variable names.
        environment: Environment mapping.

    Returns:
        Parsed integer value if available, otherwise `None`.
    """
    for key in keys:
        raw_value = environment.get(key)
        if raw_value is None:
            continue

        try:
            return int(raw_value)
        except ValueError:
            continue

    return None


def _read_positive_int(
    keys: Sequence[str], environment: Mapping[str, str]
) -> Optional[int]:
    """Reads the first parseable positive integer for the provided keys.

    Args:
        keys: Candidate environment variable names.
        environment: Environment mapping.

    Returns:
        Parsed positive integer if available, otherwise `None`.
    """
    value = _read_first_int(keys, environment)
    if value is None or value <= 0:
        return None
    return value


def normalize_kubeflow_trainer_distributed_env(
    environment: Optional[MutableMapping[str, str]] = None,
) -> None:
    """Normalizes Kubeflow Trainer PET variables to torch distributed env vars.

    The mapping is additive and preserves any explicitly configured torch
    environment variables.

    Args:
        environment: Mutable environment mapping. Defaults to `os.environ`.
    """
    env = environment if environment is not None else os.environ

    if "MASTER_ADDR" not in env:
        if pet_master_addr := env.get("PET_MASTER_ADDR"):
            env["MASTER_ADDR"] = pet_master_addr

    if "MASTER_PORT" not in env:
        if pet_master_port := _read_positive_int(("PET_MASTER_PORT",), env):
            env["MASTER_PORT"] = str(pet_master_port)

    if "RANK" not in env:
        pet_node_rank = _read_first_int(("PET_NODE_RANK",), env)
        if pet_node_rank is not None:
            env["RANK"] = str(pet_node_rank)

    if "WORLD_SIZE" not in env:
        pet_nnodes = _read_positive_int(("PET_NNODES",), env)
        pet_nproc_per_node = _read_positive_int(("PET_NPROC_PER_NODE",), env)
        if pet_nnodes is not None and pet_nproc_per_node is not None:
            env["WORLD_SIZE"] = str(pet_nnodes * pet_nproc_per_node)

    if "LOCAL_RANK" not in env:
        pet_nproc_per_node = _read_positive_int(("PET_NPROC_PER_NODE",), env)
        if pet_nproc_per_node is not None:
            env["LOCAL_RANK"] = "0"


def get_global_rank(
    environment: Optional[Mapping[str, str]] = None,
) -> Optional[int]:
    """Returns the distributed global rank if available.

    Args:
        environment: Environment mapping. Defaults to `os.environ`.

    Returns:
        Global rank if parseable, otherwise `None`.
    """
    env = environment if environment is not None else os.environ
    return _read_first_int(_GLOBAL_RANK_KEYS, env)


def is_primary_distributed_replica(
    environment: Optional[Mapping[str, str]] = None,
) -> bool:
    """Determines whether the current process is the primary rank.

    The function prioritizes explicit global-rank environment variables. If
    those are missing but a distributed world size is available, the local rank
    is used as a best-effort fallback.

    Args:
        environment: Environment mapping. Defaults to `os.environ`.

    Returns:
        `True` if this process should be considered primary.
    """
    env = environment if environment is not None else os.environ

    global_rank = _read_first_int(_GLOBAL_RANK_KEYS, env)
    if global_rank is not None:
        return global_rank == 0

    pet_node_rank = _read_first_int(("PET_NODE_RANK",), env)
    if pet_node_rank is not None:
        pet_nproc_per_node = _read_positive_int(("PET_NPROC_PER_NODE",), env)
        if pet_nproc_per_node == 1:
            return pet_node_rank == 0

        local_rank = _read_first_int(_LOCAL_RANK_KEYS, env)
        if local_rank is not None:
            return pet_node_rank == 0 and local_rank == 0

    world_size = _read_first_int(_WORLD_SIZE_KEYS, env)
    if world_size is not None and world_size > 1:
        local_rank = _read_first_int(_LOCAL_RANK_KEYS, env)
        if local_rank is not None:
            return local_rank == 0

    return True
