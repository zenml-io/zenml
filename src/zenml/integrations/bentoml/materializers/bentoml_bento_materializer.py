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
"""Materializer for BentoML Bento objects."""

import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Tuple, Type

import bentoml
from bentoml._internal.bento import Bento, bento
from bentoml.exceptions import BentoMLException

from zenml.enums import ArtifactType
from zenml.integrations.bentoml.constants import DEFAULT_BENTO_FILENAME
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType

logger = get_logger(__name__)


class BentoMaterializer(BaseMaterializer):
    """Materializer for Bentoml Bento objects."""

    ASSOCIATED_TYPES: ClassVar[Tuple[Type[Any], ...]] = (bento.Bento,)
    ASSOCIATED_ARTIFACT_TYPE: ClassVar[ArtifactType] = ArtifactType.DATA

    def load(self, data_type: Type[bento.Bento]) -> bento.Bento:
        """Read from artifact store and return a Bento object.

        Args:
            data_type: An bento.Bento type.

        Returns:
            An bento.Bento object.
        """
        with self.get_temporary_directory(delete_at_exit=False) as temp_dir:
            # Copy from artifact store to temporary directory
            io_utils.copy_dir(self.uri, temp_dir)

            # Load the Bento from the temporary directory
            imported_bento = Bento.import_from(
                os.path.join(temp_dir, DEFAULT_BENTO_FILENAME)
            )

            # Try save the Bento to the local BentoML store
            try:
                _ = bentoml.get(imported_bento.tag)
            except BentoMLException:
                imported_bento.save()
            return imported_bento

    def save(self, bento: bento.Bento) -> None:
        """Write to artifact store.

        Args:
            bento: An bento.Bento object.
        """
        with self.get_temporary_directory(delete_at_exit=True) as temp_dir:
            temp_bento_path = os.path.join(temp_dir, DEFAULT_BENTO_FILENAME)
            bentoml.export_bento(bento.tag, temp_bento_path)
            io_utils.copy_dir(temp_dir, self.uri)

    def extract_metadata(
        self, bento: bento.Bento
    ) -> Dict[str, "MetadataType"]:
        """Extract metadata from the given `Bento` object.

        Args:
            bento: The `Bento` object to extract metadata from.

        Returns:
            The extracted metadata as a dictionary.
        """
        return {
            "bento_info_name": bento.info.name,
            "bento_info_version": bento.info.version,
            "bento_tag_name": bento.tag.name,
            "bentoml_version": bento.info.bentoml_version,
        }
