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
"""Implementation of the PyTorch safetensors materializer."""

import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

from torch.nn import Module

from zenml.enums import ArtifactType
from zenml.integrations.pytorch.utils import count_module_params
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

DEFAULT_FILENAME = "model.safetensors"


class PyTorchSafetensorsMaterializer(BaseMaterializer):
    """Materializer that stores a PyTorch model's weights with safetensors.

    Unlike `PyTorchModuleMaterializer`, which pickles the model, this
    materializer writes only the model's `state_dict` in the `safetensors`
    format. Nothing is pickled, so loading an artifact never executes code
    from it.

    Because `safetensors` stores tensors and nothing else, the model class
    itself is not part of the artifact. It is recovered from the artifact type
    ZenML records at save time and passed back to `load`, which means the class
    must be constructible without arguments. This materializer is therefore not
    registered as a default for `torch.nn.Module`; select it explicitly:

    ```python
    @step(output_materializers=PyTorchSafetensorsMaterializer)
    def train() -> Module: ...
    ```
    """

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (Module,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL

    # Not registered as the default materializer for `torch.nn.Module`: it
    # requires a no-argument constructor, which existing pipelines have never
    # had to satisfy. Users opt in per output.
    SKIP_REGISTRATION: ClassVar[bool] = True

    def load(self, data_type: Type[Any]) -> Module:
        """Reads a model's weights and loads them into a new instance.

        Args:
            data_type: The type of the model to read.

        Returns:
            The model with the stored weights loaded into it.

        Raises:
            TypeError: If `data_type` cannot be instantiated without
                arguments.
        """
        from safetensors.torch import load_file

        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_file = os.path.join(temp_dir, DEFAULT_FILENAME)
            fileio.copy(os.path.join(self.uri, DEFAULT_FILENAME), temp_file)
            state_dict = load_file(temp_file)

        try:
            model: Module = data_type()
        except TypeError as e:
            raise TypeError(
                f"Unable to instantiate `{data_type.__name__}` without "
                f"arguments: {e}. The safetensors format stores tensors only, "
                f"so this materializer rebuilds the model from its class and "
                f"then loads the stored weights into it. Give the class "
                f"default values for all of its constructor arguments, or use "
                f"the default `PyTorchModuleMaterializer` instead."
            ) from e

        model.load_state_dict(state_dict)
        return model

    def save(self, model: Module) -> None:
        """Writes a model's weights in the safetensors format.

        Args:
            model: The model whose weights should be written.
        """
        from safetensors.torch import save_file

        # Detached and moved to CPU so that the artifact does not depend on the
        # device the model was trained on.
        state_dict = {
            key: value.detach().cpu()
            for key, value in model.state_dict().items()
        }

        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_file = os.path.join(temp_dir, DEFAULT_FILENAME)
            save_file(state_dict, temp_file)
            fileio.copy(temp_file, os.path.join(self.uri, DEFAULT_FILENAME))

    def extract_metadata(self, model: Module) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Model` object.

        Args:
            model: The `Model` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {**count_module_params(model)}
