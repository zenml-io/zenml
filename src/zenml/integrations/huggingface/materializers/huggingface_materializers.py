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

import importlib
import os
from typing import Any, Type

from datasets import Dataset
from datasets.dataset_dict import DatasetDict
from transformers import AutoConfig, AutoTokenizer
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from zenml.artifacts import DataArtifact, ModelArtifact
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "hf_dataset.parquet.gzip"
COMPRESSION_TYPE = "gzip"
DEFAULT_DICT_FILENAME = "hf_dict_datasets"


class HFDatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from huggingface datasets."""

    ASSOCIATED_TYPES = (Dataset, DatasetDict)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Dataset:
        """Reads Dataset"""
        super().handle_input(data_type)
        if issubclass(data_type, Dataset):
            return Dataset.from_parquet(
                os.path.join(self.artifact.uri, DEFAULT_FILENAME)
            )
        elif issubclass(data_type, DatasetDict):
            return DatasetDict.load_from_disk(
                os.path.join(self.artifact.uri, DEFAULT_DICT_FILENAME)
            )

    def handle_return(self, ds: Type[Any]) -> None:
        """Writes a Dataset to the specified filename.
        Args:
            Dataset: The Dataset to write.
        """
        super().handle_return(ds)
        if isinstance(ds, Dataset):
            filepath = os.path.join(self.artifact.uri, DEFAULT_FILENAME)
            ds.to_parquet(filepath, compression=COMPRESSION_TYPE)
        elif isinstance(ds, DatasetDict):
            filepath = os.path.join(self.artifact.uri, DEFAULT_DICT_FILENAME)
            ds.save_to_disk(filepath)


DEFAULT_TF_MODEL_DIR = "hf_tf_model"


class HFTFModelMaterializer(BaseMaterializer):
    """Materializer to read tensorflow model to and from huggingface pretrained model."""

    from transformers import TFPreTrainedModel

    ASSOCIATED_TYPES = (TFPreTrainedModel,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> TFPreTrainedModel:
        """Reads HFModel"""
        super().handle_input(data_type)

        config = AutoConfig.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TF_MODEL_DIR)
        )
        architecture = "TF" + config.architectures[0]
        model_cls = getattr(
            importlib.import_module("transformers"), architecture
        )
        return model_cls.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TF_MODEL_DIR)
        )

    def handle_return(self, model: Type[Any]) -> None:
        """Writes a Model to the specified dir.
        Args:
            HFModel: The Model to write.
        """
        super().handle_return(model)
        model.save_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TF_MODEL_DIR)
        )


DEFAULT_PT_MODEL_DIR = "hf_pt_model"


class HFPTModelMaterializer(BaseMaterializer):
    """Materializer to read torch model to and from huggingface pretrained model."""

    from transformers import PreTrainedModel

    ASSOCIATED_TYPES = (PreTrainedModel,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> PreTrainedModel:
        """Reads HFModel"""
        super().handle_input(data_type)

        config = AutoConfig.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_PT_MODEL_DIR)
        )
        architecture = config.architectures[0]
        model_cls = getattr(
            importlib.import_module("transformers"), architecture
        )
        return model_cls.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_PT_MODEL_DIR)
        )

    def handle_return(self, model: Type[Any]) -> None:
        """Writes a Model to the specified dir.
        Args:
            HFModel: The Model to write.
        """
        super().handle_return(model)
        model.save_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_PT_MODEL_DIR)
        )


DEFAULT_TOKENIZER_DIR = "hf_tokenizer"


class HFTokenizerMaterializer(BaseMaterializer):
    """Materializer to read tokenizer to and from huggingface tokenizer."""

    ASSOCIATED_TYPES = (PreTrainedTokenizerBase,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> PreTrainedTokenizerBase:
        """Reads Tokenizer"""
        super().handle_input(data_type)

        return AutoTokenizer.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TOKENIZER_DIR)
        )

    def handle_return(self, tokenizer: Type[Any]) -> None:
        """Writes a Tokenizer to the specified dir.
        Args:
            HFTokenizer: The Tokenizer to write.
        """
        super().handle_return(tokenizer)
        tokenizer.save_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TOKENIZER_DIR)
        )
