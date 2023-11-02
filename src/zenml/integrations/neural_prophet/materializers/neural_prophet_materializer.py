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
"""Implementation of the Neural Prophet materializer."""

from typing import Any, ClassVar, Tuple, Type

from neuralprophet import NeuralProphet

from zenml.enums import ArtifactType
from zenml.integrations.pytorch.materializers.base_pytorch_materializer import (
    BasePyTorchMaterializer,
)

# TODO [ENG-794]: The integration consists of a simple materializer that uses the
#  torch load and save methods which is the [current recommended way of storing
#  NeuralProphet models on disk](https://github.com/ourownstory/neural_prophet/issues/27).
#  Update this once a better implementation is exposed.

DEFAULT_FILENAME = "entire_model.pt"


class NeuralProphetMaterializer(BasePyTorchMaterializer):
    """Materializer to read/write NeuralProphet models."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (NeuralProphet,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
    FILENAME: ClassVar[str] = DEFAULT_FILENAME
