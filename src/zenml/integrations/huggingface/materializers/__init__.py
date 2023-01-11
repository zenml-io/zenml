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
"""Initialization of Huggingface materializers."""

from zenml.integrations.huggingface.materializers.huggingface_datasets_materializer import (
    HFDatasetMaterializer,
)
from zenml.integrations.huggingface.materializers.huggingface_pt_model_materializer import (
    HFPTModelMaterializer,
)
from zenml.integrations.huggingface.materializers.huggingface_tf_model_materializer import (
    HFTFModelMaterializer,
)
from zenml.integrations.huggingface.materializers.huggingface_tokenizer_materializer import (
    HFTokenizerMaterializer,
)
