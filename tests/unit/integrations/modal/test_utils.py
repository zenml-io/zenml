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
"""Tests for Modal integration utility helpers."""

from zenml.integrations.modal.utils import map_resource_settings


def test_map_resource_settings_omits_none_by_default() -> None:
    """Tests that resource kwargs omit `None` values by default."""
    kwargs = map_resource_settings(cpu=1.5, memory_mb=None, gpu=None)

    assert kwargs == {"cpu": 1.5}


def test_map_resource_settings_includes_none_values_when_requested() -> None:
    """Tests that `include_none=True` keeps all expected resource keys."""
    kwargs = map_resource_settings(
        cpu=None,
        memory_mb=None,
        gpu=None,
        include_none=True,
    )

    assert kwargs == {"cpu": None, "memory": None, "gpu": None}


def test_map_resource_settings_maps_all_values() -> None:
    """Tests mapping of CPU, memory, and GPU values."""
    kwargs = map_resource_settings(cpu=2.0, memory_mb=2048, gpu="A10G")

    assert kwargs == {"cpu": 2.0, "memory": 2048, "gpu": "A10G"}
