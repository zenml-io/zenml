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
from contextlib import ExitStack as does_not_raise

import pytest
from pydantic import ValidationError

from zenml.config.resource_configuration import ByteUnit, ResourceConfiguration


def test_unit_byte_value_defined_for_all_values():
    """Tests that the byte value is defined for all enum cases."""
    for unit in ByteUnit:
        assert unit.byte_value > 0


def test_resource_config_empty():
    """Tests that the empty property is only True when no value is configured."""
    assert ResourceConfiguration().empty is True
    assert ResourceConfiguration(cpu_count=1).empty is False
    assert ResourceConfiguration(gpu_count=1).empty is False
    assert ResourceConfiguration(memory="1KB").empty is False


def test_resource_config_value_validation():
    """Tests that the attribute values get correctly validated."""
    # CPU
    with pytest.raises(ValidationError):
        ResourceConfiguration(cpu_count=-13)

    with pytest.raises(ValidationError):
        ResourceConfiguration(cpu_count=-101.7)

    with does_not_raise():
        ResourceConfiguration(cpu_count=0.3)
        ResourceConfiguration(cpu_count=12.41)

    # GPU
    with pytest.raises(ValidationError):
        ResourceConfiguration(gpu_count=-1)

    with does_not_raise():
        ResourceConfiguration(gpu_count=1)
        ResourceConfiguration(gpu_count=2)

    # Memory
    with pytest.raises(ValidationError):
        ResourceConfiguration(memory="1 KB")

    with pytest.raises(ValidationError):
        ResourceConfiguration(memory="-1KB")

    with pytest.raises(ValidationError):
        ResourceConfiguration(memory="KB")

    with pytest.raises(ValidationError):
        ResourceConfiguration(memory="1AB")

    with does_not_raise():
        ResourceConfiguration(memory="1KB")
        ResourceConfiguration(memory="200MiB")
        ResourceConfiguration(memory="31GB")
        ResourceConfiguration(memory="42PiB")


def test_resource_config_memory_conversion():
    """Tests that the memory value gets correctly converted."""
    r = ResourceConfiguration(memory="1KB")
    assert r.get_memory(unit="KB") == 1
    assert r.get_memory(unit="MB") == 1 / 1000

    r = ResourceConfiguration(memory="1000MB")
    assert r.get_memory(unit="KB") == 1000 * 1000
    assert r.get_memory(unit="MB") == 1000
    assert r.get_memory(unit="GB") == 1

    r = ResourceConfiguration(memory="11GiB")
    assert r.get_memory(unit="KiB") == 11 * 1024 * 1024
    assert r.get_memory(unit="MiB") == 11 * 1024
    assert r.get_memory(unit="GiB") == 11
