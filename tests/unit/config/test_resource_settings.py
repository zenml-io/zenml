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

from zenml.config.resource_settings import ByteUnit, ResourceSettings


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


def test_pool_resources_empty_dict_merges_to_empty() -> None:
    """Empty pool_resources is accepted; merged map has no keys from the map."""
    rs = ResourceSettings(pool_resources={})
    assert rs.empty is True
    assert rs.merged_requested_resources() == {}


def test_merged_requested_resources_from_pool_resources_only() -> None:
    """Custom keys pass through when typed resource fields are unset."""
    rs = ResourceSettings(pool_resources={"tpu": 2, "widgets": 3})
    assert rs.merged_requested_resources() == {"tpu": 2, "widgets": 3}


def test_merged_requested_resources_typed_fields_override_pool_resources() -> (
    None
):
    """gpu_count, cpu_count, and memory override duplicate dict keys."""
    rs = ResourceSettings(
        pool_resources={"gpu": 9, "mcpu": 1, "memory_mb": 1},
        gpu_count=2,
        cpu_count=1.0,
        memory="512MB",
    )
    merged = rs.merged_requested_resources()
    assert merged["gpu"] == 2
    assert merged["mcpu"] == 1000
    assert merged["memory_mb"] == 512


def test_merged_requested_resources_gpu_count_zero_clears_gpu() -> None:
    """gpu_count zero removes gpu from the merged map."""
    rs = ResourceSettings(pool_resources={"gpu": 2}, gpu_count=0)
    assert "gpu" not in rs.merged_requested_resources()


def test_merged_requested_resources_legacy_equivalent() -> None:
    """Behavior matches the former StackComponent.get_requested_resources logic."""
    rs = ResourceSettings(cpu_count=2.5, gpu_count=1, memory="1GB")
    assert rs.merged_requested_resources() == {
        "gpu": 1,
        "mcpu": 2500,
        "memory_mb": 1000,
    }


def test_empty_property_excludes_pool_resources() -> None:
    """empty stays True when only pool_resources is set.

    pool_resources are for resource-pool scheduling; they are not part of the
    generic resource fields that orchestrators and step operators consume.
    """
    rs = ResourceSettings(pool_resources={"x": 1})
    assert rs.empty is True
