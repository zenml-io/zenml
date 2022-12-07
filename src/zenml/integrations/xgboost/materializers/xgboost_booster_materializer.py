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
"""Implementation of an XGBoost booster materializer."""

import os
import tempfile
from typing import Any, Type

import xgboost as xgb

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "model.json"


class XgboostBoosterMaterializer(BaseMaterializer):
    """Materializer to read data to and from xgboost.Booster."""

    ASSOCIATED_TYPES = (xgb.Booster,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> xgb.Booster:
        """Reads a xgboost Booster model from a serialized JSON file.

        Args:
            data_type: A xgboost Booster type.

        Returns:
            A xgboost Booster object.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Create a temporary folder
        temp_dir = tempfile.mkdtemp(prefix="zenml-temp-")
        temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

        # Copy from artifact store to temporary file
        fileio.copy(filepath, temp_file)
        booster = xgb.Booster()
        booster.load_model(temp_file)

        # Cleanup and return
        fileio.rmtree(temp_dir)
        return booster

    def save(self, booster: xgb.Booster) -> None:
        """Creates a JSON serialization for a xgboost Booster model.

        Args:
            booster: A xgboost Booster model.
        """
        super().save(booster)

        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Make a temporary phantom artifact
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            booster.save_model(f.name)
            # Copy it into artifact store
            fileio.copy(f.name, filepath)

        # Close and remove the temporary file
        f.close()
        fileio.remove(f.name)
