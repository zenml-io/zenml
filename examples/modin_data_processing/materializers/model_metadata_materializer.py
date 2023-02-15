# Apache Software License 2.0
# 
# Copyright (c) ZenML GmbH 2023. All rights reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# 
import os
from typing import Type

import yaml

from artifacts import ModelMetadata

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class ModelMetadataMaterializer(BaseMaterializer):
    """Custom materializer for the `ModelMetadata` artifact data type.

    A materializer instructs ZenML about how to store (de-materialize)
    the information from an artifact data type (ModelMetadata in this example)
    into the artifact store and, conversely, loading (materializing) it back
    into the artifact data type. Take a look at the `artifacts` folder for
    additional information about custom artifact data types.

    When using custom data types for your artifacts, you must also supply
    a custom materializer class that implements two simple I/O operations:

     - saving an artifact object to the the artifact store
     - loading an artifact object from the artifact store

    For both of these operations, the ZenML framework supplies a URI
    (`self.uri`) identifying the location in the artifact store where the
    artifact is/should be located. Implementing them means transferring
    the in-memory data stored in the artifact to the provided URI and
    vice-versa. ZenML puts at your disposal a series of I/O utilities capable of
    universally handling these URLs in the `zenml.io.fileio`,
    `zenml.utils.io_utils` and `zenml.utils.yaml_utils` Python modules.  

    More information about custom step artifact data types and ZenML
    materializers is available in the docs:

      https://docs.zenml.io/advanced-guide/pipelines/materializers
    
    """

    # This needs to point to the artifact data type(s) associated with the
    # materializer 
    ASSOCIATED_TYPES = (ModelMetadata,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.STATISTICS

    def save(self, model_metadata: ModelMetadata) -> None:
        """Save (de-materialize) a model metadata artifact to the artifact store.

        This operation takes the information in the artifact (`model_metadata`)
        and stores it in the artifact store at the `self.uri` URI location.

        This is usually implemented in one of two ways:

        - shown here: using the `zenml.io.fileio.open()` function or one of the
        `zenml.utils.yaml_utils` wrappers to write the artifact data
        directly to a file in the artifact store, similar to how you would use
        the standard `open()` Python I/O.
        - saving the artifact to a temporary location on your local filesystem
        and then copying it to the artifact store using the `zenml.io.fileio`
        functions (e.g. `mkdir()`, `copy()`). This last method is used in
        cases where artifact data types come from 3rd party libraries that are
        not directly aware of ZenML's I/O and cannot be modified to use it.

        Args:
            model_metadata: model metadata object to save to the artifact store.            
        """
        super().save(model_metadata)

        ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
        # Dump the model metadata directly into the artifact store as a YAML file
        with fileio.open(os.path.join(self.uri, 'model_metadata.yaml'), 'w') as f:
            f.write(yaml.dump(model_metadata.metadata))
        ### YOUR CODE ENDS HERE ###

    def load(self, data_type: Type[ModelMetadata]) -> ModelMetadata:
        """Load (materialize) a model metadata artifact from the artifact store.

        This operation takes the `self.uri` URI location in the artifact store
        and loads the information present at that location in an artifact
        object (`ModelMetadata`).

        This is usually implemented in one of two ways:

        - shown here: using the `zenml.io.fileio.open()` function or one of the
        `zenml.utils.yaml_utils` wrappers to read the artifact data
        directly from a file in the artifact store, similar to how you would use
        the standard `open()` Python I/O.
        - copying the artifact from the artifact store to a temporary location
        on your local filesystem using the `zenml.io.fileio` functions (e.g.
        `copy()`) and loading the information from the local file into the
        artifact instance. This last method is used in cases where artifact data
        types come from 3rd party libraries that are not directly aware of
        ZenML's I/O and cannot be modified to use it.

        Args:
            data_type: the artifact data type (model metadata)
        
        Returns:
            A model metadata artifact instance materialized from the artifact
            store.
        """
        super().load(data_type)

        ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
        with fileio.open(os.path.join(self.uri, 'data.txt'), 'r') as f:
            model_metadata = ModelMetadata()
            model_metadata.metadata = yaml.safe_load(f.read())
        ### YOUR CODE ENDS HERE ###

        return model_metadata
