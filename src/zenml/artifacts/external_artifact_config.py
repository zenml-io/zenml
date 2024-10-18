#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""External artifact definition."""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, model_validator

from zenml.logger import get_logger
from zenml.utils.pydantic_utils import before_validator_handler

logger = get_logger(__name__)


class ExternalArtifactConfiguration(BaseModel):
    """External artifact configuration.

    Lightweight class to pass in the steps for runtime inference.
    """

    id: Optional[UUID] = None

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _remove_old_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove old attributes that are not used anymore.

        Args:
            data: The model data.

        Returns:
            Model data without the removed attributes.
        """
        data.pop("name", None)
        data.pop("version", None)
        data.pop("model", None)
        return data

    def get_artifact_version_id(self) -> UUID:
        """Get the artifact.

        Returns:
            The artifact ID.

        Raises:
            RuntimeError: If the artifact store of the referenced artifact
                is not the same as the one in the active stack.
            RuntimeError: If neither the ID nor the name of the artifact was
                provided.
        """
        from zenml.client import Client

        client = Client()

        if self.id:
            response = client.get_artifact_version(self.id)
        else:
            raise RuntimeError(
                "The ID of the artifact must be provided. "
                "- If you created this ExternalArtifact from a value, please "
                "ensure that `upload_by_value` was called before trying to "
                "fetch the artifact ID.\n- If you specified an artifact name "
                "or model name for this external artifact, this functionality "
                "was removed from the ExternalArtifact class. Use Client "
                "methods instead to dynamically fetch an artifact via name or "
                "from a model instead."
            )

        artifact_store_id = client.active_stack.artifact_store.id
        if response.artifact_store_id != artifact_store_id:
            raise RuntimeError(
                f"The artifact {response.name} (ID: {response.id}) "
                "referenced by an external artifact is not stored in the "
                "artifact store of the active stack. This will lead to "
                "issues loading the artifact. Please make sure to only "
                "reference artifact versions stored in your active artifact "
                "store."
            )

        return self.id
