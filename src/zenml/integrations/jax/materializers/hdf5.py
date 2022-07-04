#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of the Scipy Sparse Materializer."""

import os
from typing import Any, Type

import h5py
import jax.numpy as jnp


from zenml.artifacts import ModelArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DATA_FILENAME = "model.h5"


class HDF5Materializer(BaseMaterializer):
    """Materializer to read and write model weights to and from HDF5 files."""

    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Any:
        """
        Reads model weights from a HDF5 file and initializes a Haiku model with them.
        This returns the weights as a flat mapping only; initialization of the
        neural network is left to the user.

        Args:
            data_type: The type of the model to load.

        Returns:
            A flat params object holding the network parameters.
        """
        with fileio.open(
            os.path.join(self.artifact.uri, DATA_FILENAME), "rb"
        ) as f:

            hf = h5py.File(f, 'r')

            params = dict()
            for name, group in hf.items():
                # layers (weights + biases) are arranged in h5.Groups
                weights = dict()
                for k, v in group.items():
                    weights[k] = jnp.asarray(v)

                params[name] = weights

            return params

    def handle_return(self, params: Any) -> None:
        """Writes a haiku model to the artifact store as a HDF5 file.

        Args:
            params: The model parameters to write.
        """
        with fileio.open(
            os.path.join(self.artifact.uri, DATA_FILENAME), "wb"
        ) as f:
            hf = h5py.File(f, 'w')

            for name, param_dict in params.items():
                # create a group for the corresponding param dict
                group = hf.create_group(name=name)
                # Haiku organizes all layer params in nested dicts,
                # so no isinstance checks are necessary here
                for k, v in param_dict.items():
                    group[k] = v
