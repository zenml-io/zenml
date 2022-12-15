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
"""Implementation of the Spark Model Materializer."""

import os
from typing import Any, Type, Union

from pyspark.ml import Estimator, Model, Transformer

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILEPATH = "model"


class SparkModelMaterializer(BaseMaterializer):
    """Materializer to read/write Spark models."""

    ASSOCIATED_TYPES = (Transformer, Estimator, Model)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(
        self, model_type: Type[Any]
    ) -> Union[Transformer, Estimator, Model]:  # type: ignore[type-arg]
        """Reads and returns a Spark ML model.

        Args:
            model_type: The type of the model to read.

        Returns:
            A loaded spark model.
        """
        super().load(model_type)
        path = os.path.join(self.uri, DEFAULT_FILEPATH)
        return model_type.load(path)  # type: ignore[no-any-return]

    def save(
        self, model: Union[Transformer, Estimator, Model]  # type: ignore[type-arg]
    ) -> None:
        """Writes a spark model.

        Args:
            model: A spark model.
        """
        super().save(model)

        # Write the dataframe to the artifact store
        path = os.path.join(self.uri, DEFAULT_FILEPATH)
        model.save(path)  # type: ignore[union-attr]
