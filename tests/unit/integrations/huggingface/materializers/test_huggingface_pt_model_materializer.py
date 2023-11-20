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

from transformers import RobertaConfig, RobertaModel

from tests.unit.test_general import _test_materializer
from zenml.integrations.huggingface.materializers.huggingface_pt_model_materializer import (
    HFPTModelMaterializer,
)


def test_huggingface_pretrained_model_materializer(clean_workspace):
    """Tests whether the steps work for the Huggingface Pretrained Model materializer."""
    model = _test_materializer(
        step_output=RobertaModel(RobertaConfig()),
        materializer_class=HFPTModelMaterializer,
        expected_metadata_size=5,
    )

    assert model.config.model_type == "roberta"
