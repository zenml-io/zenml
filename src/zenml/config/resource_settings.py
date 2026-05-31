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
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional, Union

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

    B = "B"
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
            ByteUnit.B: 1,
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

ResourceInput = Union[
    str,
    Dict[str, PositiveInt],
    "PoolResourceDemand",
    List["PoolResourceDemand"],
]
"""Flexible resource pool demand input accepted by ``ResourceSettings.resources``.

May be:

* a resource name string (quantity defaults to 1),
* a name-to-quantity map (for example ``{"tpu": 2}``),
* one ``PoolResourceDemand``,
* a list of demands or demand dictionaries.
"""


class PoolResourceDemand(BaseSettings):
    """Resource pool demand used by ResourceSettings.

    Attributes:
        name: Resource descriptor name.
        quantity: Requested quantity.
        kind: Optional resource kind (for example ``gpu``).
        unit: Optional unit for the requested quantity.
        class_name: Optional exact capacity class name.
        resource_selector: Optional selector over resource descriptor fields and
            attributes.
        class_selector: Optional selector over capacity class fields and
            attributes.
    """

    name: str = Field(min_length=1)
    quantity: PositiveInt
    kind: Optional[str] = Field(default=None, min_length=1)
    unit: Optional[str] = Field(default=None, min_length=1)
    class_name: Optional[str] = Field(
        default=None,
        alias="class",
        serialization_alias="class",
    )
    resource_selector: Optional[Dict[str, Any]] = None
    class_selector: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        populate_by_name=True,
        # prevent extra attributes during model initialization
        extra="ignore",
    )


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
        gpu_class: Optional GPU capacity class for resource pool scheduling.
        memory: The amount of memory that should be configured.
        resources: Resource pool demands (``ResourceInput``). After validation
            this is a list of ``PoolResourceDemand``. Legacy ``pool_resources``
            and ``pool_resource_demands`` inputs are still accepted and folded
            into this field.
        reclaim_tolerance: Capacity reclaim behavior tolerated by resource pool
            requests. Defaults to ``any`` when not set. Legacy ``preemptible``
            booleans are still accepted on input and mapped into this field.
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
    """

    cpu_count: Optional[PositiveFloat] = None
    gpu_count: Optional[NonNegativeInt] = None
    gpu_class: Optional[str] = None
    memory: Optional[str] = Field(pattern=MEMORY_REGEX, default=None)
    resources: ResourceInput = Field(
        default_factory=list,
        description=(
            "Resource pool demands. Accepts a resource name, a name-to-quantity "
            "map, one PoolResourceDemand, or a list of demands."
        ),
    )
    reclaim_tolerance: ResourceRequestReclaimTolerance = (
        ResourceRequestReclaimTolerance.ANY
    )

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
    def normalize_input(cls, data: Any) -> Any:
        """Normalize legacy and flexible resource settings input.

        Args:
            data: Raw input data supplied to the model.

        Returns:
            Input data with ``resources`` and ``reclaim_tolerance`` populated.
        """
        if not isinstance(data, dict):
            return data

        normalized = dict(data)

        if normalized.get("reclaim_tolerance") is None:
            preemptible = normalized.get("preemptible")
            if preemptible is True:
                normalized["reclaim_tolerance"] = (
                    ResourceRequestReclaimTolerance.COORDINATED
                )
            elif preemptible is False:
                normalized["reclaim_tolerance"] = (
                    ResourceRequestReclaimTolerance.NONE
                )

        if normalized.get("resources") is None:
            if normalized.get("pool_resources") is not None:
                normalized["resources"] = normalized["pool_resources"]

        normalized.pop("preemptible", None)
        normalized.pop("pool_resources", None)
        return normalized

    @property
    def normalized_resources(self) -> List[PoolResourceDemand]:
        """Normalized resources field.

        Returns:
            List of normalized resource demands.
        """
        if isinstance(self.resources, str):
            return [PoolResourceDemand(name=self.resources, quantity=1)]
        if isinstance(self.resources, PoolResourceDemand):
            return [self.resources]
        if isinstance(self.resources, dict):
            return [
                PoolResourceDemand(name=name, quantity=quantity)
                for name, quantity in self.resources.items()
            ]
        return self.resources

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
        generic resource-related values are configured. This excludes pool
        ``resources`` and ``reclaim_tolerance``, which are only relevant for
        resource pool scheduling and currently ignored by workload scheduling
        stack components like orchestrators and step operators.

        Returns:
            `True` if no values were configured, `False` otherwise.
        """
        return (
            len(
                self.model_dump(
                    exclude_unset=True,
                    exclude_none=True,
                    exclude={
                        "resources",
                        "reclaim_tolerance",
                        "gpu_class",
                    },
                )
            )
            == 0
        )

    def get_memory(
        self, unit: Union[str, "ByteUnit"] = ByteUnit.GB
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
        for memory_unit in sorted(
            ByteUnit, key=lambda unit: len(unit.value), reverse=True
        ):
            if memory.endswith(memory_unit.value):
                memory_value = int(memory[: -len(memory_unit.value)])
                return memory_value * memory_unit.byte_value / unit.byte_value
        else:
            # Should never happen due to the regex validation
            raise ValueError(f"Unable to parse memory unit from '{memory}'.")

    def memory_quantity_and_unit(self) -> Optional[tuple[int, ByteUnit]]:
        """Parse the configured memory string into quantity and unit.

        Returns:
            Quantity and ``ByteUnit`` parsed from ``memory``, or None when
            memory is not configured.

        Raises:
            ValueError: If ``memory`` is set but does not end with a known
                byte unit suffix.
        """
        if not self.memory:
            return None

        for memory_unit in sorted(
            ByteUnit, key=lambda unit: len(unit.value), reverse=True
        ):
            if self.memory.endswith(memory_unit.value):
                quantity = int(self.memory[: -len(memory_unit.value)])
                return quantity, memory_unit

        raise ValueError(f"Unable to parse memory unit from '{self.memory}'.")

    def merged_resource_demands(self) -> list["ResourceRequestDemand"]:
        """Build canonical Resource Manager demands for pool allocation.

        Pool ``resources`` and typed CPU/GPU/memory fields are converted into
        separate demands without merging or overriding.

        Returns:
            Resource demand entries for pool scheduling.
        """
        from zenml.models import ResourceRequestDemand

        demands = [
            ResourceRequestDemand(
                resource=demand.name,
                quantity=demand.quantity,
                kind=demand.kind,
                unit=demand.unit,
                class_name=demand.class_name,
                resource_selector=demand.resource_selector,
                class_selector=demand.class_selector,
            )
            for demand in self.normalized_resources
        ]

        if self.gpu_count is not None and self.gpu_count > 0:
            demands.append(
                ResourceRequestDemand(
                    kind="gpu",
                    quantity=self.gpu_count,
                    class_name=self.gpu_class,
                )
            )

        if self.cpu_count is not None:
            demands.append(
                ResourceRequestDemand(
                    kind="cpu",
                    quantity=math.ceil(self.cpu_count),
                    unit="CPU",
                )
            )

        memory_spec = self.memory_quantity_and_unit()
        if memory_spec is not None:
            memory_quantity, memory_unit = memory_spec
            demands.append(
                ResourceRequestDemand(
                    kind="memory",
                    quantity=memory_quantity,
                    unit=memory_unit.value,
                )
            )

        return demands

    model_config = ConfigDict(
        # public attributes are immutable
        frozen=True,
        # prevent extra attributes during model initialization
        extra="ignore",
    )
