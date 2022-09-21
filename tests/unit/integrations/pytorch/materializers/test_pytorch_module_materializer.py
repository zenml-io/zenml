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

from torch.nn import Linear, Module

from tests.unit.test_general import _test_materializer
from zenml.integrations.pytorch.materializers.pytorch_module_materializer import (
    PyTorchModuleMaterializer,
)


def test_pytorch_module_materializer(clean_repo):
    """Tests whether the steps work for the Sklearn materializer."""
    with does_not_raise():
        _test_materializer(
            step_output=Linear(20, 20),
            materializer=PyTorchModuleMaterializer,
        )

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    module = last_run.steps[-1].output.read()
    assert isinstance(module, Module)
    assert module.in_features == 20
    assert module.out_features == 20
    assert module.bias is not None
