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
import json
import os
from typing import Any, Dict, Optional

import kserve
from ml_metadata.proto import metadata_store_pb2

from zenml.logger import get_logger
from zenml.utils import source_utils
from zenml.utils.source_utils import import_class_by_path

logger = get_logger(__name__)

ARTIFACT_FILE = "artifact.json"


class ZenMLCustomModel(kserve.Model):
    def __init__(
        self,
        model_name: str,
        model_uri: str,
        predict_func: str,
        load_func: Optional[str],
    ):
        super().__init__(model_name)
        self.name = model_name
        self.model_uri = model_uri
        if load_func is not None:
            self.load_func = import_class_by_path(load_func)
        self.predict_func = import_class_by_path(predict_func)
        self.model = None
        self.ready = False

    def load(self) -> bool:
        model_file_dir = kserve.Storage.download(self.model_dir, self.name)
        if self.load_func is not None:
            try:
                self.model = self.load_func()
            except Exception as e:
                logger.error("Failed to load model: {}".format(e))
                return False
            self.ready = True
            return self.ready
        else:
            try:
                self.model = self._load_model_with_zenml_artifact(
                    model_file_dir
                )
            except Exception as e:
                logger.error("Failed to load model: {}".format(e))
                return False
            self.ready = True
            return self.ready

    def predict(self, request: Dict) -> Dict:
        """Predict the given request.

        Args:
            request: The request to predict in a dictionary. e.g. {"instances": []}

        Returns:
            The prediction in a dictionary. e.g. {"predictions": []}
        """
        if self.predict_func is not None:
            try:
                prediction = self.predict_func(request)
            except Exception as e:
                logger.error("Failed to predict: {}".format(e))
                return None
            return prediction
        else:
            raise NotImplementedError("Predict function is not implemented")

    def _load_model_with_zenml_artifact(self, model_file_dir: str) -> Any:
        artifact_file = os.path.join(model_file_dir, ARTIFACT_FILE)
        with open(artifact_file) as json_file:
            artifact = json.load(json_file)
        model_artifact = metadata_store_pb2.Artifact()
        model_artifact.uri = model_file_dir
        model_artifact.properties["datatype"].string_value = artifact[
            "datatype"
        ]
        model_artifact.properties["materializer"].string_value = artifact[
            "materializer"
        ]
        materializer_class = source_utils.load_source_path_class(
            model_artifact.properties["materializer"].string_value
        )
        model_class = source_utils.load_source_path_class(
            model_artifact.properties["datatype"].string_value
        )
        materialzer_object = materializer_class(model_artifact)
        model = materialzer_object.handle_input(model_class)
        return model
