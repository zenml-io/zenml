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
from typing import Any, ClassVar, Tuple, Type

import xgboost as xgb

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "model.json"


class XgboostBoosterMaterializer(BaseMaterializer):
    """Materializer to read data to and from xgboost.Booster."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (xgb.Booster,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL

    def load(self, data_type: Type[Any]) -> xgb.Booster:
        """Reads a xgboost Booster model from a serialized JSON file.

        Args:
            data_type: A xgboost Booster type.

        Returns:
            A xgboost Booster object.
        """
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)

            # Copy from artifact store to temporary file
            fileio.copy(filepath, temp_file)
            booster = xgb.Booster()
            booster.load_model(temp_file)

            return booster

    def save(self, booster: xgb.Booster) -> None:
        """Creates a JSON serialization for a xgboost Booster model.

        Args:
            booster: A xgboost Booster model.
        """
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_file = os.path.join(str(temp_dir), DEFAULT_FILENAME)
            with open(temp_file, "w"):
                booster.save_model(temp_file)

            fileio.copy(temp_file, filepath)
