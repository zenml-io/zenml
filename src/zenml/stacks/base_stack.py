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
from typing import TYPE_CHECKING, Any, Dict, Optional

from pydantic import BaseSettings, PrivateAttr

from zenml.enums import StackTypes

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.container_registries import BaseContainerRegistry
    from zenml.metadata_stores import BaseMetadataStore
    from zenml.orchestrators import BaseOrchestrator


class BaseStack(BaseSettings):
    """Base stack for ZenML.

    A ZenML stack brings together a Metadata Store, an Artifact Store, and
    an Orchestrator, the trifecta of the environment required to run a ZenML
    pipeline. A ZenML stack also happens to be a pydantic `BaseSettings`
    class, which means that there are multiple ways to use it.

    * You can set it via env variables.
    * You can set it through the config yaml file.
    * You can set it in code by initializing an object of this class, and
        passing it to pipelines as a configuration.

    In the case where a value is specified for the same Settings field in
    multiple ways, the selected value is determined as follows (in descending
    order of priority):

    * Arguments passed to the Settings class initializer.
    * Environment variables, e.g. zenml_var as described above.
    * Variables loaded from a config yaml file.
    * The default field values.
    """

    stack_type: StackTypes = StackTypes.base
    metadata_store_name: str
    artifact_store_name: str
    orchestrator_name: str
    container_registry_name: Optional[str] = None
    _repo_path: Optional[str] = PrivateAttr(default=None)

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        """Removes private attributes from pydantic dict so they don't get
        stored in our config files."""
        return {
            key: value
            for key, value in super().dict(**kwargs).items()
            if not key.startswith("_")
        }

    @property
    def orchestrator(self) -> "BaseOrchestrator":
        """Returns the orchestrator of this stack."""
        from zenml.core.repo import Repository

        return Repository(self._repo_path).service.get_orchestrator(
            self.orchestrator_name
        )

    @property
    def artifact_store(self) -> "BaseArtifactStore":
        """Returns the artifact store of this stack."""
        from zenml.core.repo import Repository

        return Repository(self._repo_path).service.get_artifact_store(
            self.artifact_store_name
        )

    @property
    def metadata_store(self) -> "BaseMetadataStore":
        """Returns the metadata store of this stack."""
        from zenml.core.repo import Repository

        return Repository(self._repo_path).service.get_metadata_store(
            self.metadata_store_name
        )

    @property
    def container_registry(self) -> Optional["BaseContainerRegistry"]:
        """Returns the optional container registry of this stack."""
        if self.container_registry_name:
            from zenml.core.repo import Repository

            return Repository(self._repo_path).service.get_container_registry(
                self.container_registry_name
            )
        else:
            return None

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_stack_"
