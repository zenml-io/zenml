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

import os
from typing import Any, Type

from pytorch_lightning.trainer import Trainer

from zenml.artifacts import ModelArtifact
from zenml.materializers.base_materializer import BaseMaterializer

CHECKPOINT_NAME = "final_checkpoint.ckpt"


class PyTorchLightningMaterializer(BaseMaterializer):
    """Materializer to read/write Pytorch models."""

    ASSOCIATED_TYPES = (Trainer,)
    ASSOCIATED_ARTIFACT_TYPES = (ModelArtifact,)

    def handle_input(self, data_type: Type[Any]) -> Trainer:
        """Reads and returns a PyTorch Lightning trainer.

        Returns:
            A PyTorch Lightning trainer object.
        """
        super().handle_input(data_type)
        return Trainer(
            resume_from_checkpoint=os.path.join(
                self.artifact.uri, CHECKPOINT_NAME
            )
        )

    def handle_return(self, trainer: Trainer) -> None:
        """Writes a PyTorch Lightning trainer.

        Args:
            trainer: A PyTorch Lightning trainer object.
        """
        super().handle_return(trainer)
        trainer.save_checkpoint(
            os.path.join(self.artifact.uri, CHECKPOINT_NAME)
        )
