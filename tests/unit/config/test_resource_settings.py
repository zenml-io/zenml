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
"""Tests for ResourceSettings and ByteUnit."""

from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from zenml.config.resource_settings import (
    ByteUnit,
    PoolResourceDemand,
    ResourceSettings,
)
from zenml.enums import ResourceRequestReclaimTolerance


def test_unit_byte_value_defined_for_all_values():
    """Tests that the byte value is defined for all enum cases."""
    for unit in ByteUnit:
        assert unit.byte_value > 0


def test_resource_config_empty():
    """Tests that the empty property is only True when no value is configured."""
    assert ResourceSettings().empty is True
    assert (
        ResourceSettings(cpu_count=None, gpu_count=None, memory=None).empty
        is True
    )
    assert ResourceSettings(cpu_count=1).empty is False
    assert ResourceSettings(gpu_count=1).empty is False
    assert ResourceSettings(memory="1KB").empty is False


def test_resource_config_value_validation():
    """Tests that the attribute values get correctly validated."""
    # CPU
    with pytest.raises(ValidationError):
        ResourceSettings(cpu_count=-13)

    with pytest.raises(ValidationError):
        ResourceSettings(cpu_count=-101.7)

    with does_not_raise():
        ResourceSettings(cpu_count=0.3)
        ResourceSettings(cpu_count=12.41)

    # GPU
    with pytest.raises(ValidationError):
        ResourceSettings(gpu_count=-1)

    with does_not_raise():
        ResourceSettings(gpu_count=1)
        ResourceSettings(gpu_count=2)

    # Memory
    with pytest.raises(ValidationError):
        ResourceSettings(memory="1 KB")

    with pytest.raises(ValidationError):
        ResourceSettings(memory="-1KB")

    with pytest.raises(ValidationError):
        ResourceSettings(memory="KB")

    with pytest.raises(ValidationError):
        ResourceSettings(memory="1AB")

    with does_not_raise():
        ResourceSettings(memory="1KB")
        ResourceSettings(memory="200MiB")
        ResourceSettings(memory="31GB")
        ResourceSettings(memory="42PiB")


def test_resource_config_memory_conversion():
    """Tests that the memory value gets correctly converted."""
    r = ResourceSettings(memory="1KB")
    assert r.get_memory(unit="KB") == 1
    assert r.get_memory(unit="MB") == 1 / 1000

    r = ResourceSettings(memory="1000MB")
    assert r.get_memory(unit="KB") == 1000 * 1000
    assert r.get_memory(unit="MB") == 1000
    assert r.get_memory(unit="GB") == 1

    r = ResourceSettings(memory="11GiB")
    assert r.get_memory(unit="KiB") == 11 * 1024 * 1024
    assert r.get_memory(unit="MiB") == 11 * 1024
    assert r.get_memory(unit="GiB") == 11


def test_memory_quantity_and_unit_parses_configured_suffix() -> None:
    """memory_quantity_and_unit returns the literal quantity and ByteUnit."""
    rs = ResourceSettings(memory="512MB")
    assert rs.memory_quantity_and_unit() == (512, ByteUnit.MB)

    rs = ResourceSettings(memory="11GiB")
    assert rs.memory_quantity_and_unit() == (11, ByteUnit.GIB)


def test_resources_empty_dict_normalizes_to_empty_list() -> None:
    """Empty resource maps are accepted and normalize to no demands."""
    rs = ResourceSettings(resources={})
    assert rs.empty is True
    assert rs.resources == {}
    assert rs.normalized_resources == []
    assert rs.merged_resource_demands() == []


def test_resources_from_name_to_quantity_map() -> None:
    """Name-to-quantity maps normalize into pool demands."""
    rs = ResourceSettings(resources={"tpu": 2, "widgets": 3})
    assert rs.resources == {"tpu": 2, "widgets": 3}
    assert [demand.name for demand in rs.normalized_resources] == [
        "tpu",
        "widgets",
    ]
    assert [demand.quantity for demand in rs.normalized_resources] == [2, 3]


def test_resources_from_string_defaults_quantity_to_one() -> None:
    """A bare resource name becomes a single-quantity demand."""
    rs = ResourceSettings(resources="tpu")
    assert rs.resources == "tpu"
    assert rs.normalized_resources == [
        PoolResourceDemand(name="tpu", quantity=1),
    ]


def test_legacy_pool_resources_input_is_normalized() -> None:
    """Legacy pool_resources input is folded into resources."""
    rs = ResourceSettings(pool_resources={"tpu": 2})
    assert rs.resources == {"tpu": 2}
    assert rs.normalized_resources[0].name == "tpu"
    assert rs.normalized_resources[0].quantity == 2


def test_resources_from_pool_resource_demand_list() -> None:
    """A list of PoolResourceDemand values is accepted via resources."""
    rs = ResourceSettings(
        resources=[
            PoolResourceDemand(name="gpu", quantity=2, kind="gpu"),
        ]
    )
    assert rs.normalized_resources[0].name == "gpu"
    assert rs.normalized_resources[0].kind == "gpu"


def test_merged_resource_demands_keeps_pool_and_typed_fields_separate() -> (
    None
):
    """Pool resources and typed fields become separate kind-based demands."""
    rs = ResourceSettings(
        resources={"tpu": 2},
        gpu_count=2,
        cpu_count=1.0,
        memory="512MB",
        gpu_class="h100",
    )
    demands = rs.merged_resource_demands()
    assert demands[0].resource == "tpu"
    assert demands[0].quantity == 2
    assert demands[1].kind == "gpu"
    assert demands[1].resource is None
    assert demands[1].quantity == 2
    assert demands[1].class_name == "h100"
    assert demands[2].kind == "cpu"
    assert demands[2].unit == "CPU"
    assert demands[2].quantity == 1
    assert demands[3].kind == "memory"
    assert demands[3].unit == ByteUnit.MB.value
    assert demands[3].quantity == 512


def test_merged_resource_demands_gpu_count_zero_omits_gpu() -> None:
    """gpu_count zero does not add a GPU demand."""
    rs = ResourceSettings(gpu_count=0)
    assert rs.merged_resource_demands() == []


def test_merged_resource_demands_typed_fields_use_kind_convention() -> None:
    """Typed fields map to kind/unit conventions instead of resource names."""
    rs = ResourceSettings(cpu_count=2.5, gpu_count=1, memory="1GB")
    demands = rs.merged_resource_demands()
    assert demands[0].kind == "gpu"
    assert demands[0].quantity == 1
    assert demands[1].kind == "cpu"
    assert demands[1].unit == "CPU"
    assert demands[1].quantity == 3
    assert demands[2].kind == "memory"
    assert demands[2].unit == ByteUnit.GB.value
    assert demands[2].quantity == 1


def test_empty_property_excludes_resources() -> None:
    """empty stays True when only pool resources are configured."""
    rs = ResourceSettings(resources={"x": 1})
    assert rs.empty is True


def test_legacy_preemptible_maps_to_reclaim_tolerance() -> None:
    """Legacy preemptible input is accepted without storing the field."""
    rs = ResourceSettings(preemptible=True)
    assert rs.reclaim_tolerance is ResourceRequestReclaimTolerance.COORDINATED
    assert "preemptible" not in rs.model_dump()

    rs = ResourceSettings(preemptible=False)
    assert rs.reclaim_tolerance is ResourceRequestReclaimTolerance.NONE
