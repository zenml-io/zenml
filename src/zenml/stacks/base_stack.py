from typing import TYPE_CHECKING, Optional

from pydantic import BaseSettings

from zenml.enums import StackTypes

if TYPE_CHECKING:
    from zenml.artifact_stores.base_artifact_store import BaseArtifactStore
    from zenml.container_registry.base_container_registry import (
        BaseContainerRegistry,
    )
    from zenml.metadata.base_metadata_store import BaseMetadataStore
    from zenml.orchestrators.base_orchestrator import BaseOrchestrator


class BaseStack(BaseSettings):
    """Base stack for ZenML.

    A ZenML stack brings together an Metadata Store, an Artifact Store, and
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

    @property
    def orchestrator(self) -> "BaseOrchestrator":
        """Returns the orchestrator of this stack."""
        from zenml.core.repo import Repository

        return Repository().service.get_orchestrator(self.orchestrator_name)

    @property
    def artifact_store(self) -> "BaseArtifactStore":
        """Returns the artifact store of this stack."""
        from zenml.core.repo import Repository

        return Repository().service.get_artifact_store(self.artifact_store_name)

    @property
    def metadata_store(self) -> "BaseMetadataStore":
        """Returns the metadata store of this stack."""
        from zenml.core.repo import Repository

        return Repository().service.get_metadata_store(self.metadata_store_name)

    @property
    def container_registry(self) -> Optional["BaseContainerRegistry"]:
        """Returns the optional container registry of this stack."""
        if self.container_registry_name:
            from zenml.core.repo import Repository

            return Repository().service.get_container_registry(
                self.container_registry_name
            )
        else:
            return None

    class Config:
        """Configuration of settings."""

        env_prefix = "zenml_stack_"
