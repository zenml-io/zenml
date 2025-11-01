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

from typing import Any, ClassVar

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
from zenml.materializers.cloudpickle_materializer import (
    CloudpickleMaterializer,
)


class SklearnMaterializer(CloudpickleMaterializer):
    """Materializer to read data to and from sklearn."""

    ASSOCIATED_TYPES: ClassVar[tuple[type[Any], ...]] = (
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
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.MODEL
