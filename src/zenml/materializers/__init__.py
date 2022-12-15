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
"""Initialization of ZenML materializers.

Materializers are used to convert a ZenML artifact into a specific format. They
are most often used to handle the input or output of ZenML steps, and can be
extended by building on the `BaseMaterializer` class.
"""


from zenml.materializers.built_in_materializer import (
    BuiltInContainerMaterializer,
    BuiltInMaterializer,
    BytesMaterializer,
)
from zenml.materializers.numpy_materializer import NumpyMaterializer
from zenml.materializers.pandas_materializer import PandasMaterializer
from zenml.materializers.service_materializer import ServiceMaterializer
from zenml.materializers.unmaterialized_artifact import UnmaterializedArtifact

__all__ = [
    "BuiltInContainerMaterializer",
    "BuiltInMaterializer",
    "BytesMaterializer",
    "NumpyMaterializer",
    "PandasMaterializer",
    "ServiceMaterializer",
    "UnmaterializedArtifact",
]
