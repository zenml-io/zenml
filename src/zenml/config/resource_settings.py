#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Resource settings class used to specify resources for a step."""

from __future__ import annotations

import math
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, Union
from uuid import UUID

from pydantic import (
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    model_validator,
)

from zenml.config.base_settings import BaseSettings
from zenml.enums import ResourceRequestReclaimTolerance

if TYPE_CHECKING:
    from zenml.models import ResourceRequestDemand


class ByteUnit(Enum):
    """Enum for byte units."""

    KB = "KB"
    KIB = "KiB"
    MB = "MB"
    MIB = "MiB"
    GB = "GB"
    GIB = "GiB"
    TB = "TB"
    TIB = "TiB"
    PB = "PB"
    PIB = "PiB"

    @property
    def byte_value(self) -> int:
        """Returns the amount of bytes that this unit represents.

        Returns:
            The byte value of this unit.
        """
        return {
            ByteUnit.KB: 10**3,
            ByteUnit.KIB: 1 << 10,
            ByteUnit.MB: 10**6,
            ByteUnit.MIB: 1 << 20,
            ByteUnit.GB: 10**9,
            ByteUnit.GIB: 1 << 30,
            ByteUnit.TB: 10**12,
            ByteUnit.TIB: 1 << 40,
            ByteUnit.PB: 10**15,
            ByteUnit.PIB: 1 << 50,
        }[self]


MEMORY_REGEX = r"^[0-9]+(" + "|".join(unit.value for unit in ByteUnit) + r")$"


class PoolResourceDemand(BaseSettings):
    """Extended resource pool demand used by ResourceSettings.

    Attributes:
        resource_id: Optional exact resource descriptor ID.
        resource: Optional exact resource descriptor name.
        quantity: Requested quantity.
        class_name: Optional exact capacity class name.
        resource_selector: Optional selector over resource descriptor fields and
            attributes.
        class_selector: Optional selector over capacity class fields and
            attributes.
    """

    resource_id: Optional[UUID] = None
    resource: Optional[str] = None
    quantity: PositiveInt
    class_name: Optional[str] = Field(
        default=None,
        alias="class",
        serialization_alias="class",
    )
    resource_selector: Optional[Dict[str, Any]] = None
    class_selector: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _validate_resource_reference(self) -> "PoolResourceDemand":
        """Validate that the demand can resolve to a resource.

        Returns:
            The validated demand.

        Raises:
            ValueError: If no resource reference or selector is configured.
        """
        if (
            self.resource_id is None
            and self.resource is None
            and self.resource_selector is None
        ):
            raise ValueError(
                "Pool resource demands require a resource ID, resource name, "
                "or resource selector."
            )
        return self

    model_config = ConfigDict(populate_by_name=True)


class ResourceSettings(BaseSettings):
    """Hardware resource settings.

    Deployers and deployed pipelines can also use the following settings:

    * min_replicas and max_replicas allow expressing both fixed scaling and
    autoscaling range. For a fixed number of instances, set both to the same
    value (e.g. 3). If min_replicas=0, it indicates the service can scale down
    to zero instances when idle (if the platform supports it) most serverless
    platforms do. If max_replicas is None or 0, it will be interpreted as
    “no specific limit” (use platform default behavior, which might be unlimited
    or a high default cap). Otherwise, max_replicas puts an upper bound on
    scaling.

    * autoscaling_metric and autoscaling_target describe when to scale. For
    example, autoscaling_metric="cpu", autoscaling_target=75.0 means keep CPU
    around 75% - a Kubernetes integration would create an HPA with target CPU
    75%, whereas a Knative integration might ignore this if it's using
    concurrency-based autoscaling. Similarly, "concurrency" with a target of,
    say, 50 means the system should try to ensure each instance handles ~50
    concurrent requests before spawning a new instance. The integration code for
    each platform will translate these generically: e.g. Cloud Run doesn't allow
    changing the CPU threshold (fixed ~60%), so it might ignore a custom CPU
    target; Knative supports concurrency and RPS metrics via annotations
    so those would be applied if specified.

    * max_concurrency is a per-instance concurrency limit. This is particularly
    useful for platforms that allow configuring a concurrency cap (Knative's
    containerConcurrency, Cloud Run's concurrency setting, App Runner's max
    concurrent requests, Modal's max_inputs in the concurrent decorator). If
    set, this indicates “do not send more than this many simultaneous requests
    to one instance.” The autoscaler will then naturally create more instances
    once this limit is hit on each existing instance. If
    autoscaling_metric="concurrency" and no explicit target is given, one could
    assume the target is equal to max_concurrency (or a certain utilization of
    it). In some cases, platforms use a utilization factor - for simplicity, we
    let the integration decide (some might use 80% of max concurrency as the
    trigger to scale, for example, if that platform does so internally). If
    max_concurrency is not set, it implies no fixed limit per instance (the
    service instance will take as many requests as it can, scaling purely on
    the chosen metric like CPU or an internal default concurrency).

    Attributes:
        cpu_count: The amount of CPU cores that should be configured.
        gpu_count: The amount of GPUs that should be configured.
        gpu_type: Optional GPU type selector for resource pool scheduling.
        gpu_class: Optional GPU capacity class for resource pool scheduling.
        memory: The amount of memory that should be configured.
        preemptible: Legacy flag for whether resource pool requests can be
            preempted. If set and ``reclaim_tolerance`` is omitted, ``True``
            maps to ``coordinated`` and ``False`` maps to ``none``.
        reclaim_tolerance: Capacity reclaim behavior tolerated by resource pool
            requests. Defaults to ``unsafe`` when neither this nor the legacy
            preemptible flag is set.
        min_replicas: Minimum number of container instances (replicas).
            Use 0 to allow scale-to-zero on idle. Only relevant to
            deployed pipelines.
        max_replicas: Maximum number of container instances for autoscaling.
            Set to 0 to imply "no explicit limit". Only relevant to deployed
            pipelines.
        autoscaling_metric: Metric to use for autoscaling triggers.
            Options: "cpu", "memory", "concurrency", or "rps". Only relevant
            to deployed pipelines.
        autoscaling_target: Target value for the autoscaling metric (e.g. 70.0
            for 70% CPU or 20 for concurrency). Only relevant to deployed
            pipelines.
        max_concurrency: Maximum concurrent requests per instance (if supported
            by the platform). Defines a concurrency limit for each container.
            Only relevant to deployed pipelines.
        pool_resources: Optional map of resource name to positive integer amount
            for ZenML resource pools. Use for custom keys
            (for example ``tpu``) or to supply ``gpu`` / ``mcpu`` / ``memory_mb``
            without the typed fields. When ``gpu_count``, ``cpu_count``, or
            ``memory`` is set, those fields override the same keys in this map.
        pool_resource_demands: Extended resource pool demands with selectors
            and class constraints.
    """

    cpu_count: Optional[PositiveFloat] = None
    gpu_count: Optional[NonNegativeInt] = None
    gpu_type: Optional[str] = None
    gpu_class: Optional[str] = None
    memory: Optional[str] = Field(pattern=MEMORY_REGEX, default=None)
    pool_resources: Optional[Dict[str, PositiveInt]] = Field(
        default=None,
        description=(
            "Maps resource names to positive integer amounts allocated from "
            "ZenML resource pools. Examples: {'memory': 2}, {'tpu': 4}, "
            "{'vcpus': 2}, {'gpus': 4}. When gpu_count, cpu_count, or memory "
            "is set, those fields override the gpu, mcpu, and memory_mb keys "
            "respectively."
        ),
    )
    pool_resource_demands: Optional[list[PoolResourceDemand]] = Field(
        default=None,
        description=(
            "Extended resource pool demands with optional exact resources, "
            "capacity classes, resource selectors, and class selectors."
        ),
    )
    reclaim_tolerance: ResourceRequestReclaimTolerance = (
        ResourceRequestReclaimTolerance.UNSAFE
    )
    preemptible: Optional[bool] = None

    # Settings only applicable for deployers and deployed pipelines
    min_replicas: Optional[NonNegativeInt] = None
    max_replicas: Optional[NonNegativeInt] = None
    autoscaling_metric: Optional[
        Literal["cpu", "memory", "concurrency", "rps"]
    ] = None
    autoscaling_target: Optional[PositiveFloat] = None
    max_concurrency: Optional[PositiveInt] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_reclaim_tolerance(cls, data: Any) -> Any:
        """Normalize legacy preemptible settings into reclaim tolerance.

        Args:
            data: Raw input data supplied to the model.

        Returns:
            Input data with ``reclaim_tolerance`` populated when possible.
        """
        if not isinstance(data, dict):
            return data

        if data.get("reclaim_tolerance") is not None:
            return data

        normalized = dict(data)
        preemptible = normalized.get("preemptible")
        if preemptible is True:
            normalized["reclaim_tolerance"] = (
                ResourceRequestReclaimTolerance.COORDINATED
            )
        elif preemptible is False:
            normalized["reclaim_tolerance"] = (
                ResourceRequestReclaimTolerance.NONE
            )

        return normalized

    @model_validator(mode="after")
    def validate_replicas(self) -> "ResourceSettings":
        """Validate that min_replicas is not greater than max_replicas.

        Returns:
            The validated settings.

        Raises:
            ValueError: If min_replicas > max_replicas.
        """
        if (
            self.min_replicas is not None
            and self.max_replicas is not None
            and self.max_replicas > 0  # 0 means "no limit"
            and self.min_replicas > self.max_replicas
        ):
            raise ValueError(
                f"min_replicas ({self.min_replicas}) cannot be greater than "
                f"max_replicas ({self.max_replicas})"
            )
        return self

    @property
    def empty(self) -> bool:
        """Returns if this object is "empty" or not.

        A ResourceSettings instance is considered empty if none of the
        generic resource-related values are configured. This excludes the
        preemptible flag and the pool_resources map, which are only relevant
        for resource pool scheduling and currently ignored by workload
        scheduling stack components like orchestrators and step operators.

        Returns:
            `True` if no values were configured, `False` otherwise.
        """
        # To detect whether this config is empty (= no values specified), we
        # check if there are any attributes which are explicitly set to any
        # value other than `None`. Exclude preemptible and pool_resources
        # because they are not part of the set of unified resource settings
        # that are understood and applied by orchestrators and step operators.
        return (
            len(
                self.model_dump(
                    exclude_unset=True,
                    exclude_none=True,
                    exclude={
                        "preemptible",
                        "pool_resources",
                        "pool_resource_demands",
                        "reclaim_tolerance",
                        "gpu_type",
                        "gpu_class",
                    },
                )
            )
            == 0
        )

    def get_memory(
        self, unit: Union[str, ByteUnit] = ByteUnit.GB
    ) -> Optional[float]:
        """Gets the memory configuration in a specific unit.

        Args:
            unit: The unit to which the memory should be converted.

        Raises:
            ValueError: If the memory string is invalid.

        Returns:
            The memory configuration converted to the requested unit, or None
            if no memory was configured.
        """
        if not self.memory:
            return None

        if isinstance(unit, str):
            unit = ByteUnit(unit)

        memory = self.memory
        for memory_unit in ByteUnit:
            if memory.endswith(memory_unit.value):
                memory_value = int(memory[: -len(memory_unit.value)])
                return memory_value * memory_unit.byte_value / unit.byte_value
        else:
            # Should never happen due to the regex validation
            raise ValueError(f"Unable to parse memory unit from '{memory}'.")

    def merged_requested_resources(self) -> Dict[str, int]:
        """Build the resource request map for scheduling and pool allocation.

        Returns:
            Resource name to amount.
        """
        merged: Dict[str, int] = (
            dict(self.pool_resources) if self.pool_resources else {}
        )

        if self.gpu_count is not None:
            if self.gpu_count > 0:
                merged["gpu"] = self.gpu_count
            else:
                merged.pop("gpu", None)

        if self.cpu_count is not None:
            merged["mcpu"] = math.ceil(self.cpu_count * 1000)

        memory_amount = self.get_memory(unit=ByteUnit.MB)
        if memory_amount is not None:
            merged["memory_mb"] = math.ceil(memory_amount)

        return merged

    def merged_resource_demands(self) -> list["ResourceRequestDemand"]:
        """Build canonical Resource Manager demands for pool allocation.

        Returns:
            Resource demand entries including compatibility shorthand resources
            and extended selector-based demands.
        """
        from zenml.models import ResourceRequestDemand

        demands = [
            ResourceRequestDemand(
                resource_id=demand.resource_id,
                resource=demand.resource,
                quantity=demand.quantity,
                class_name=demand.class_name,
                resource_selector=demand.resource_selector,
                class_selector=demand.class_selector,
            )
            for demand in self.pool_resource_demands or []
        ]

        for resource, quantity in self.merged_requested_resources().items():
            if resource == "gpu" and (
                self.gpu_type is not None or self.gpu_class is not None
            ):
                selector = {"kind": "gpu"}
                if self.gpu_type is not None:
                    selector["gpu_type"] = self.gpu_type

                demands.append(
                    ResourceRequestDemand(
                        resource=resource,
                        quantity=quantity,
                        class_name=self.gpu_class,
                        resource_selector=selector,
                    )
                )
            else:
                demands.append(
                    ResourceRequestDemand(
                        resource=resource,
                        quantity=quantity,
                    )
                )

        return demands

    model_config = ConfigDict(
        # public attributes are immutable
        frozen=True,
        # prevent extra attributes during model initialization
        extra="ignore",
    )
