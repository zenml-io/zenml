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
"""Implementation of the sklearn materializer."""

import os
import pickle
from typing import Any, Type, Union

from sklearn.base import (
    BaseEstimator,
    BiclusterMixin,
    ClassifierMixin,
    ClusterMixin,
    DensityMixin,
    MetaEstimatorMixin,
    MultiOutputMixin,
    OutlierMixin,
    RegressorMixin,
    TransformerMixin,
)

from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "model"


class SklearnMaterializer(BaseMaterializer):
    """Materializer to read data to and from sklearn."""

    ASSOCIATED_TYPES = (
        BaseEstimator,
        ClassifierMixin,
        ClusterMixin,
        BiclusterMixin,
        OutlierMixin,
        RegressorMixin,
        MetaEstimatorMixin,
        MultiOutputMixin,
        DensityMixin,
        TransformerMixin,
    )
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.MODEL

    def load(
        self, data_type: Type[Any]
    ) -> Union[
        BaseEstimator,
        ClassifierMixin,
        ClusterMixin,
        BiclusterMixin,
        OutlierMixin,
        RegressorMixin,
        MetaEstimatorMixin,
        MultiOutputMixin,
        DensityMixin,
        TransformerMixin,
    ]:
        """Reads a base sklearn model from a pickle file.

        Args:
            data_type: The type of the model.

        Returns:
            The model.
        """
        super().load(data_type)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        with fileio.open(filepath, "rb") as fid:
            clf = pickle.load(fid)
        return clf

    def save(
        self,
        clf: Union[
            BaseEstimator,
            ClassifierMixin,
            ClusterMixin,
            BiclusterMixin,
            OutlierMixin,
            RegressorMixin,
            MetaEstimatorMixin,
            MultiOutputMixin,
            DensityMixin,
            TransformerMixin,
        ],
    ) -> None:
        """Creates a pickle for a sklearn model.

        Args:
            clf: A sklearn model.
        """
        super().save(clf)
        filepath = os.path.join(self.uri, DEFAULT_FILENAME)
        with fileio.open(filepath, "wb") as fid:
            pickle.dump(clf, fid)
