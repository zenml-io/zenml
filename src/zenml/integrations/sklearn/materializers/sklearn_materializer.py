"""Implementation of the sklearn materializer."""

import os
from typing import Any, ClassVar, Tuple, Type

import cloudpickle
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
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.materializers.cloudpickle_materializer import (
    DEFAULT_FILENAME,
    CloudpickleMaterializer,
)

logger = get_logger(__name__)

SKLEARN_MODEL_FILENAME = "model.pkl"


class SklearnMaterializer(CloudpickleMaterializer):
    """Materializer to read data to and from sklearn with backward compatibility."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (
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

    def load(self, data_type: Type[Any]) -> Any:
        """Reads a sklearn model from pickle file with backward compatibility.

        Args:
            data_type: The data type of the artifact.

        Returns:
            The loaded sklearn model.
        """
        # First try to load from model.pkl
        model_filepath = os.path.join(self.uri, SKLEARN_MODEL_FILENAME)
        artifact_filepath = os.path.join(self.uri, DEFAULT_FILENAME)

        # Check which file exists and load accordingly
        if self.artifact_store.exists(model_filepath):
            filepath = model_filepath
        elif self.artifact_store.exists(artifact_filepath):
            logger.info(
                f"Loading from legacy filepath {artifact_filepath}. Future saves "
                f"will use {model_filepath}"
            )
            filepath = artifact_filepath
        else:
            raise FileNotFoundError(
                f"Neither {model_filepath} nor {artifact_filepath} found in artifact store"
            )

        # validate python version before loading
        source_python_version = self._load_python_version()
        current_python_version = Environment().python_version()
        if (
            source_python_version != "unknown"
            and source_python_version != current_python_version
        ):
            logger.warning(
                f"Your artifact was materialized under Python version "
                f"'{source_python_version}' but you are currently using "
                f"'{current_python_version}'. This might cause unexpected "
                "behavior since pickle is not reproducible across Python "
                "versions. Attempting to load anyway..."
            )

        # Load the model
        with self.artifact_store.open(filepath, "rb") as fid:
            return cloudpickle.load(fid)

    def save(self, data: Any) -> None:
        """Saves a sklearn model to pickle file using the new filename.

        Args:
            data: The sklearn model to save.
        """
        # Save python version for validation on loading
        self._save_python_version()

        # Save using the new filename
        filepath = os.path.join(self.uri, SKLEARN_MODEL_FILENAME)
        with self.artifact_store.open(filepath, "wb") as fid:
            cloudpickle.dump(data, fid)
