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

import os
from typing import Any, Type

import xgboost as xgb

from zenml.artifacts import ModelArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "model.json"


class XgboostBoosterMaterializer(BaseMaterializer):
    """Materializer to read data to and from xgboost."""

    ASSOCIATED_TYPES = (xgb.Booster,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> xgb.Booster:
        """Reads a base xgboost model from a serialized JSON file."""
        super().handle_input(data_type)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        booster = xgb.Booster()
        with fileio.open(filepath, "rb") as fid:
            booster.load_model(fid)
        return booster

    def handle_return(self, booster: xgb.Booster) -> None:
        """Creates a JSON serialization for a xgboost model.

        Args:
            booster: A xgboost booster model.
        """
        super().handle_return(booster)
        filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
        with fileio.open(filepath, "wb") as fid:
            booster.save_model(fid)
