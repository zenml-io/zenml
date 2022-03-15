import os
from typing import Any, Type

from datasets import Dataset
from datasets.dataset_dict import DatasetDict
from transformers import (
    DistilBertTokenizerFast,
    TFDistilBertForTokenClassification,
)

from zenml.artifacts import DataArtifact, ModelArtifact
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_FILENAME = "dataset.parquet.gzip"
COMPRESSION_TYPE = "gzip"
DEFAULT_DICT_FILENAME = "dict_datasets"


class DatasetMaterializer(BaseMaterializer):
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


DEFAULT_MODEL_DIR = "hf_model"


class HFModelMaterializer(BaseMaterializer):
    """Materializer to read model to and from huggingface pretrained model."""

    ASSOCIATED_TYPES = (TFDistilBertForTokenClassification,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Dataset:
        """Reads Model"""
        super().handle_input(data_type)

        return TFDistilBertForTokenClassification.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_MODEL_DIR)
        )

    def handle_return(self, model: Type[Any]) -> None:
        """Writes a Model to the specified dir.
        Args:
            TFDistilBertForTokenClassification: The Model to write.
        """
        super().handle_return(model)
        model.save_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_MODEL_DIR)
        )


DEFAULT_TOKENIZER_DIR = "hf_tokenizer"


class HFTokenizerMaterializer(BaseMaterializer):
    """Materializer to read tokenizer to and from huggingface tokenizer."""

    ASSOCIATED_TYPES = (DistilBertTokenizerFast,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> DistilBertTokenizerFast:
        """Reads Tokenizer"""
        super().handle_input(data_type)

        return DistilBertTokenizerFast.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TOKENIZER_DIR)
        )

    def handle_return(self, tokenizer: Type[Any]) -> None:
        """Writes a Tokenizer to the specified dir.
        Args:
            DistilBertTokenizerFast: The Tokenizer to write.
        """
        super().handle_return(tokenizer)
        tokenizer.save_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_TOKENIZER_DIR)
        )
