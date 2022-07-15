import os
import tempfile
from typing import Type


from fastai.learner import Learner, load_learner

from zenml.artifacts import ModelArtifact
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer

DEFAULT_MODEL_FILENAME = "model.pkl"

logger = get_logger(__name__)


class FastaiLearnerMaterializer(BaseMaterializer):
    """Materializer to read/write fastai models."""

    ASSOCIATED_TYPES = (Learner,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Learner]) -> Learner:
        """Reads and returns a fastai model.
        Only loads the model, not the checkpoint.

        Args:
            data_type: The type of the model to load.
        Returns:
            A loaded fastai model.
        """
        super().handle_input(data_type)

        from steps.model_trainer_step import is_aria

        with tempfile.TemporaryDirectory() as d:
            fileio.copy(
                os.path.join(self.artifact.uri, DEFAULT_MODEL_FILENAME),
                os.path.join(d, DEFAULT_MODEL_FILENAME),
            )
            return load_learner(os.path.join(d, DEFAULT_MODEL_FILENAME))

    def handle_return(self, model: Learner) -> None:
        """Writes a fastai model along with its optimizer state.

        Args:
            model: A fastai model
        """
        super().handle_return(model)

        from steps.model_trainer_step import is_aria

        # Save entire model to artifact directory
        with tempfile.TemporaryDirectory() as d:
            model.export(os.path.join(d, DEFAULT_MODEL_FILENAME))
            fileio.copy(
                os.path.join(d, DEFAULT_MODEL_FILENAME),
                os.path.join(self.artifact.uri, DEFAULT_MODEL_FILENAME),
            )
