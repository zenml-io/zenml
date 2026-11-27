"""Workspace-managed deployment component with explicit package intents."""

from typing import ClassVar, NoReturn, Optional, Type
from uuid import UUID

from zenml.client import Client
from zenml.managed_models.client import ManagedModelClient
from zenml.model_deployers.base_model_deployer import (
    DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    BaseModelDeployer,
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)
from zenml.models.managed_model import (
    ManagedModelService,
    ManagedModelServiceRequest,
    ModelPackage,
)
from zenml.models.v2.misc.service import ServiceType
from zenml.services import BaseService, ServiceConfig


class ManagedModelDeployerConfig(BaseModelDeployerConfig):
    """Managed serving has no client-side provider credentials or endpoints."""


class ManagedModelDeployerFlavor(BaseModelDeployerFlavor):
    """Register the managed model-deployer component in ordinary ZenML stacks."""

    @property
    def name(self) -> str:
        """Get the registered flavor name.

        Returns:
            Managed flavor name.
        """
        return "managed"

    @property
    def config_class(self) -> Type[ManagedModelDeployerConfig]:
        """Get the credential-free component configuration.

        Returns:
            Managed configuration class.
        """
        return ManagedModelDeployerConfig

    @property
    def implementation_class(self) -> Type["ManagedModelDeployer"]:
        """Get the workspace API implementation.

        Returns:
            Managed deployer class.
        """
        return ManagedModelDeployer


class ManagedModelDeployer(BaseModelDeployer):
    """Submit packages through the workspace's durable managed serving API.

    Legacy BaseService operations are deliberately unsupported: they write a
    different service registry and use destructive replacement semantics.
    Lifecycle operations use ManagedModelClient and explicit generations.
    """

    NAME: ClassVar[str] = "managed"
    FLAVOR: ClassVar[Type[BaseModelDeployerFlavor]] = (
        ManagedModelDeployerFlavor
    )

    def deploy_package(
        self,
        package: ModelPackage,
        name: str,
        serving_profile: str,
        request_key: str,
        project_id: Optional[UUID] = None,
    ) -> ManagedModelService:
        """Accept a registered model package without downloading its weights.

        Args:
            package: Full-model or adapter package references.
            name: Human-readable service name.
            serving_profile: Approved versioned runtime profile.
            request_key: Stable identity preserved across pipeline retries.
            project_id: Explicit project, or the active project.

        Returns:
            Accepted service and operation, which may still be pending.
        """
        return ManagedModelClient().create(
            ManagedModelServiceRequest(
                package=package,
                name=name,
                serving_profile=serving_profile,
                model_deployer_id=self.id,
                project_id=project_id or Client().active_project.id,
            ),
            request_key,
        )

    def deploy_model(
        self,
        config: ServiceConfig,
        service_type: ServiceType,
        replace: bool = False,
        continuous_deployment_mode: bool = False,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> NoReturn:
        """Reject legacy deployment before it writes a separate service record.

        Args:
            config: Legacy service configuration.
            service_type: Legacy service type.
            replace: Legacy replacement mode.
            continuous_deployment_mode: Legacy continuous deployment mode.
            timeout: Legacy deployment timeout.

        Raises:
            NotImplementedError: Always; submit a package instead.
        """
        raise NotImplementedError(
            "Use deploy_package and ManagedModelClient lifecycle operations."
        )

    def perform_deploy_model(
        self,
        id: UUID,
        config: ServiceConfig,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> NoReturn:
        """Reject the legacy service registry entry point.

        Args:
            id: Legacy service ID.
            config: Legacy service configuration.
            timeout: Legacy timeout.

        Raises:
            NotImplementedError: Always; submit a managed package instead.
        """
        raise NotImplementedError("Use deploy_package.")

    @staticmethod
    def get_model_server_info(
        service: BaseService,
    ) -> NoReturn:
        """Reject inspection through the legacy service registry.

        Args:
            service: Legacy service record.

        Raises:
            NotImplementedError: Always; read the managed service by ID.
        """
        raise NotImplementedError(
            "Use ManagedModelClient.get with the managed service ID."
        )

    def perform_stop_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> NoReturn:
        """Reject legacy stop semantics.

        Args:
            service: Legacy service record.
            timeout: Legacy timeout.
            force: Legacy forced stop flag.

        Raises:
            NotImplementedError: Always; accept a managed pause intent instead.
        """
        raise NotImplementedError(
            "Use ManagedModelClient.mutate with action='pause'."
        )

    def perform_start_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
    ) -> NoReturn:
        """Reject legacy start semantics.

        Args:
            service: Legacy service record.
            timeout: Legacy timeout.

        Raises:
            NotImplementedError: Always; accept a managed resume intent instead.
        """
        raise NotImplementedError(
            "Use ManagedModelClient.mutate with action='resume'."
        )

    def perform_delete_model(
        self,
        service: BaseService,
        timeout: int = DEFAULT_DEPLOYMENT_START_STOP_TIMEOUT,
        force: bool = False,
    ) -> NoReturn:
        """Reject legacy synchronous deletion semantics.

        Args:
            service: Legacy service record.
            timeout: Legacy timeout.
            force: Legacy forced deletion flag.

        Raises:
            NotImplementedError: Always; accept a managed deletion intent instead.
        """
        raise NotImplementedError(
            "Use ManagedModelClient.mutate with action='delete'."
        )
