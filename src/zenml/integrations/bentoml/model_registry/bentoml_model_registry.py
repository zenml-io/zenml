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
"""Implementation for the BentoML model registry utils functionalities."""

import typing as t
import bentoml.Model as BentoModel

class BentoMLModelRegistryParameters(BaseModel):
    """BentoML model registry configuration.

    Attributes:
        
    """

    model_name: str
    model_type: str
    labels: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, str]] = None
    custom_objects: dict[str, t.Any] = None,



def bentoml_model_saver(
    params: BentoMLModelRegistryParameters,
    model: t.Any,
) -> str:
    """Saves a model to a BentoML model registry.

    Args:
        params: Parameters for the BentoML model registry.
        model: Model to be saved.
    """
    if params.model_type == "pytorch":
        bento_model: BentoModel = bentoml.pytorch.save_model(
            model=model,
            model_name=params.model_name,
            labels=params.labels,
            metadata=params.metadata,
            custom_objects=params.custom_objects,
        )
        return bento_model.path


