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


import json
import os
from typing import Type

from artifacts.model_metadata import ModelMetadata
from zenml.enums import ArtifactType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class ModelMetadataMaterializer(BaseMaterializer):
    ASSOCIATED_TYPES = (ModelMetadata,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.STATISTICS

    def load(self, data_type: Type[ModelMetadata]) -> ModelMetadata:
        """Read from artifact store.

        Args:
            data_type: What type the artifact data should be loaded as.

        Raises:
            ValueError: on deserialization issue

        Returns:
            Read artifact.
        """
        super().load(data_type)

        ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
        import sklearn.ensemble
        import sklearn.linear_model
        import sklearn.tree

        modules = [sklearn.ensemble, sklearn.linear_model, sklearn.tree]

        with fileio.open(os.path.join(self.uri, "data.json"), "r") as f:
            data_json = json.loads(f.read())
        class_name = data_json["model_class"]
        cls = None
        for module in modules:
            if cls := getattr(module, class_name, None):
                break
        if cls is None:
            raise ValueError(
                f"Cannot deserialize `{class_name}` using {self.__class__.__name__}. "
                f"Only classes from modules {[m.__name__ for m in modules]} "
                "are supported"
            )
        data = ModelMetadata(cls)
        if "search_grid" in data_json:
            data.search_grid = data_json["search_grid"]
        if "params" in data_json:
            data.params = data_json["params"]
        if "metric" in data_json:
            data.metric = data_json["metric"]
        ### YOUR CODE ENDS HERE ###

        return data

    def save(self, data: ModelMetadata) -> None:
        """Write to artifact store.

        Args:
            data: The data of the artifact to save.
        """
        super().save(data)

        ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
        # Dump the model metadata directly into the artifact store as a JSON file
        data_json = dict()
        with fileio.open(os.path.join(self.uri, "data.json"), "w") as f:
            data_json["model_class"] = data.model_class.__name__
            if data.search_grid:
                data_json["search_grid"] = {}
                for k, v in data.search_grid.items():
                    if type(v) == range:
                        data_json["search_grid"][k] = list(v)
                    else:
                        data_json["search_grid"][k] = v
            if data.params:
                data_json["params"] = data.params
            if data.metric:
                data_json["metric"] = data.metric
            f.write(json.dumps(data_json))
        ### YOUR CODE ENDS HERE ###
