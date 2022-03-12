from datasets import Dataset
from datasets.dataset_dict import DatasetDict
import os
from typing import Any, Type
from zenml.artifacts import DataArtifact, ModelArtifact
from zenml.materializers.base_materializer import BaseMaterializer
from transformers import TFDistilBertForTokenClassification


DEFAULT_FILENAME = "dataset.parquet.gzip"
COMPRESSION_TYPE = "gzip"
DEFAULT_DICT_FILENAME = "dict_datasets"

class DatasetMaterializer(BaseMaterializer):
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = (Dataset, DatasetDict)
    ASSOCIATED_ARTIFACT_TYPES = (
        DataArtifact,
    )

    def handle_input(self, data_type: Type[Any]) -> Dataset:
        """Reads Dataset from a parquet file."""
        super().handle_input(data_type)
        if issubclass(data_type, Dataset):
          return Dataset.from_parquet(
              os.path.join(self.artifact.uri, DEFAULT_FILENAME))
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
    """Materializer to read data to and from pandas."""

    ASSOCIATED_TYPES = (TFDistilBertForTokenClassification, )
    ASSOCIATED_ARTIFACT_TYPES = (
        ModelArtifact,
    )

    def handle_input(self, data_type: Type[Any]) -> Dataset:
        """Reads Dataset from a parquet file."""
        super().handle_input(data_type)

        return TFDistilBertForTokenClassification.from_pretrained(
            os.path.join(self.artifact.uri, DEFAULT_MODEL_DIR)
        )

    def handle_return(self, model: Type[Any]) -> None:
        """Writes a Dataset to the specified filename.
        Args:
            Dataset: The Dataset to write.
        """
        super().handle_return(model)
        model.save_pretrained(os.path.join(self.artifact.uri, DEFAULT_MODEL_DIR))