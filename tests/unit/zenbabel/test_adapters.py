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
"""Tests for ZenBabel adapters."""

import pytest

from zenml.steps.base_step import BaseStep
from zenml.zenbabel.adapters import (
    PORTABLE_STEP_ADAPTER_SOURCE,
    PortableStepAdapter,
)


def test_portable_step_adapter_loads_as_base_step():
    """Tests that the adapter has the shape pre-execution code expects."""
    step = BaseStep.load_from_source(PORTABLE_STEP_ADAPTER_SOURCE)

    assert isinstance(step, PortableStepAdapter)
    assert "PortableStepAdapter" in step.source_code
    assert "Importable marker step" in (step.docstring or "")


def test_portable_step_adapter_rejects_normal_execution():
    """Tests that accidental normal execution fails clearly."""
    step = BaseStep.load_from_source(PORTABLE_STEP_ADAPTER_SOURCE)

    with pytest.raises(RuntimeError, match="must not be executed"):
        step.entrypoint("input", parameter=1)
