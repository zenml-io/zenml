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

import os
import platform

import pytest

if platform.system() == "Windows":
    pytest.skip(
        "PyTorch integration is not installed on Windows CI.",
        allow_module_level=True,
    )

import torch
from torch.nn import Linear, Module

from tests.unit.test_general import _test_materializer
from zenml.integrations.pytorch.materializers.pytorch_module_materializer import (
    PyTorchModuleMaterializer,
)
from zenml.integrations.pytorch.materializers.pytorch_safetensors_materializer import (
    DEFAULT_FILENAME,
    PyTorchSafetensorsMaterializer,
)
from zenml.materializers.materializer_registry import materializer_registry


class LinearModule(Module):
    """A module whose constructor takes no required arguments."""

    def __init__(self) -> None:
        """Initializes the module."""
        super().__init__()
        self.linear = Linear(4, 3)


class ModuleWithRequiredArgs(Module):
    """A module that cannot be rebuilt from its class alone."""

    def __init__(self, out_features: int) -> None:
        """Initializes the module.

        Args:
            out_features: The size of the output.
        """
        super().__init__()
        self.linear = Linear(4, out_features)


def test_pytorch_safetensors_materializer(clean_client):
    """Tests that a module survives a save/load round trip unchanged."""
    module = LinearModule()

    def _only_safetensors_was_written(artifact_uri: str) -> None:
        assert os.listdir(artifact_uri) == [DEFAULT_FILENAME]

    loaded = _test_materializer(
        step_output=module,
        materializer_class=PyTorchSafetensorsMaterializer,
        validation_function=_only_safetensors_was_written,
        expected_metadata_size=3,
    )

    assert isinstance(loaded, LinearModule)
    for key, value in module.state_dict().items():
        assert torch.equal(loaded.state_dict()[key], value)


def test_pytorch_safetensors_materializer_writes_no_pickle(clean_client):
    """Tests that nothing pickled is left in the artifact directory.

    This is the point of the materializer: loading an artifact written by it
    can never execute code from that artifact.
    """

    def _nothing_pickled(artifact_uri: str) -> None:
        written = os.listdir(artifact_uri)
        assert not [name for name in written if name.endswith(".pt")]

    _test_materializer(
        step_output=LinearModule(),
        materializer_class=PyTorchSafetensorsMaterializer,
        validation_function=_nothing_pickled,
    )


def test_pytorch_safetensors_materializer_reports_a_model_it_cannot_rebuild(
    tmp_path,
):
    """Tests that a module needing constructor arguments fails clearly."""
    materializer = PyTorchSafetensorsMaterializer(uri=str(tmp_path))
    materializer.save(ModuleWithRequiredArgs(out_features=3))

    with pytest.raises(TypeError, match="without arguments"):
        materializer.load(ModuleWithRequiredArgs)


def test_pytorch_safetensors_materializer_is_not_the_default(clean_client):
    """Tests that the default materializer for a module is unchanged.

    The safetensors materializer requires a no-argument constructor, which
    existing pipelines have never had to satisfy, so it must be opted into
    rather than picked up automatically.
    """
    assert materializer_registry[Module] is PyTorchModuleMaterializer
