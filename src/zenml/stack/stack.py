#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import time
import uuid
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Dict,
    NoReturn,
    Optional,
    Set,
    Type,
)

from zenml.config.global_config import GlobalConfiguration
from zenml.enums import StackComponentType
from zenml.exceptions import ProvisioningError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.runtime_configuration import (
    RUN_NAME_OPTION_KEY,
    RuntimeConfiguration,
)
from zenml.utils import string_utils

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.container_registries import BaseContainerRegistry
    from zenml.metadata_stores import BaseMetadataStore
    from zenml.orchestrators import BaseOrchestrator
    from zenml.pipelines import BasePipeline
    from zenml.secrets_managers import BaseSecretsManager
    from zenml.stack import StackComponent
    from zenml.step_operators import BaseStepOperator


logger = get_logger(__name__)


class Stack:
    """ZenML stack class.

    A ZenML stack is a collection of multiple stack components that are
    required to run ZenML pipelines. Some of these components (orchestrator,
    metadata store and artifact store) are required to run any kind of
    pipeline, other components like the container registry are only required
    if other stack components depend on them.
    """

    def __init__(
        self,
        name: str,
        *,
        orchestrator: "BaseOrchestrator",
        metadata_store: "BaseMetadataStore",
        artifact_store: "BaseArtifactStore",
        container_registry: Optional["BaseContainerRegistry"] = None,
        secrets_manager: Optional["BaseSecretsManager"] = None,
        step_operator: Optional["BaseStepOperator"] = None,
    ):
        """Initializes and validates a stack instance.

        Raises:
             StackValidationError: If the stack configuration is not valid.
        """
        self._name = name
        self._orchestrator = orchestrator
        self._metadata_store = metadata_store
        self._artifact_store = artifact_store
        self._container_registry = container_registry
        self._step_operator = step_operator
        self._secrets_manager = secrets_manager

        self.validate()

    @classmethod
    def from_components(
        cls, name: str, components: Dict[StackComponentType, "StackComponent"]
    ) -> "Stack":
        """Creates a stack instance from a dict of stack components.

        Args:
            name: The name of the stack.
            components: The components of the stack.

        Returns:
            A stack instance consisting of the given components.

        Raises:
            TypeError: If a required component is missing or a component
                doesn't inherit from the expected base class.
        """
        from zenml.artifact_stores import BaseArtifactStore
        from zenml.container_registries import BaseContainerRegistry
        from zenml.metadata_stores import BaseMetadataStore
        from zenml.orchestrators import BaseOrchestrator
        from zenml.secrets_managers import BaseSecretsManager
        from zenml.step_operators import BaseStepOperator

        def _raise_type_error(
            component: Optional["StackComponent"], expected_class: Type[Any]
        ) -> NoReturn:
            """Raises a TypeError that the component has an unexpected type."""
            raise TypeError(
                f"Unable to create stack: Wrong stack component type "
                f"`{component.__class__.__name__}` (expected: subclass "
                f"of `{expected_class.__name__}`)"
            )

        orchestrator = components.get(StackComponentType.ORCHESTRATOR)
        if not isinstance(orchestrator, BaseOrchestrator):
            _raise_type_error(orchestrator, BaseOrchestrator)

        metadata_store = components.get(StackComponentType.METADATA_STORE)
        if not isinstance(metadata_store, BaseMetadataStore):
            _raise_type_error(metadata_store, BaseMetadataStore)

        artifact_store = components.get(StackComponentType.ARTIFACT_STORE)
        if not isinstance(artifact_store, BaseArtifactStore):
            _raise_type_error(artifact_store, BaseArtifactStore)

        container_registry = components.get(
            StackComponentType.CONTAINER_REGISTRY
        )
        if container_registry is not None and not isinstance(
            container_registry, BaseContainerRegistry
        ):
            _raise_type_error(container_registry, BaseContainerRegistry)

        secrets_manager = components.get(StackComponentType.SECRETS_MANAGER)
        if secrets_manager is not None and not isinstance(
            secrets_manager, BaseSecretsManager
        ):
            _raise_type_error(secrets_manager, BaseSecretsManager)

        step_operator = components.get(StackComponentType.STEP_OPERATOR)
        if step_operator is not None and not isinstance(
            step_operator, BaseStepOperator
        ):
            _raise_type_error(step_operator, BaseStepOperator)

        return Stack(
            name=name,
            orchestrator=orchestrator,
            metadata_store=metadata_store,
            artifact_store=artifact_store,
            container_registry=container_registry,
            secrets_manager=secrets_manager,
            step_operator=step_operator,
        )

    @classmethod
    def default_local_stack(cls) -> "Stack":
        """Creates a stack instance which is configured to run locally."""
        from zenml.artifact_stores import LocalArtifactStore
        from zenml.metadata_stores import SQLiteMetadataStore
        from zenml.orchestrators import LocalOrchestrator

        orchestrator = LocalOrchestrator(name="default")

        artifact_store_uuid = uuid.uuid4()
        artifact_store_path = os.path.join(
            GlobalConfiguration().config_directory,
            "local_stores",
            str(artifact_store_uuid),
        )
        fileio.create_dir_recursive_if_not_exists(artifact_store_path)
        artifact_store = LocalArtifactStore(
            name="default",
            uuid=artifact_store_uuid,
            path=artifact_store_path,
        )

        metadata_store_path = os.path.join(artifact_store_path, "metadata.db")
        metadata_store = SQLiteMetadataStore(
            name="default", uri=metadata_store_path
        )

        return cls(
            name="default",
            orchestrator=orchestrator,
            metadata_store=metadata_store,
            artifact_store=artifact_store,
        )

    @property
    def components(self) -> Dict[StackComponentType, "StackComponent"]:
        """All components of the stack."""
        return {
            component.type: component
            for component in [
                self.orchestrator,
                self.metadata_store,
                self.artifact_store,
                self.container_registry,
                self.secrets_manager,
                self.step_operator,
            ]
            if component is not None
        }

    @property
    def name(self) -> str:
        """The name of the stack."""
        return self._name

    @property
    def orchestrator(self) -> "BaseOrchestrator":
        """The orchestrator of the stack."""
        return self._orchestrator

    @property
    def metadata_store(self) -> "BaseMetadataStore":
        """The metadata store of the stack."""
        return self._metadata_store

    @property
    def artifact_store(self) -> "BaseArtifactStore":
        """The artifact store of the stack."""
        return self._artifact_store

    @property
    def container_registry(self) -> Optional["BaseContainerRegistry"]:
        """The container registry of the stack."""
        return self._container_registry

    @property
    def secrets_manager(self) -> Optional["BaseSecretsManager"]:
        """The secrets manager of the stack."""
        return self._secrets_manager

    @property
    def step_operator(self) -> Optional["BaseStepOperator"]:
        """The step operator of the stack."""
        return self._step_operator

    @property
    def runtime_options(self) -> Dict[str, Any]:
        """Runtime options that are available to configure this stack.

        This method combines the available runtime options for all components
        of this stack. See `StackComponent.runtime_options()` for
        more information.
        """
        runtime_options: Dict[str, Any] = {}
        for component in self.components.values():
            duplicate_runtime_options = (
                runtime_options.keys() & component.runtime_options.keys()
            )
            if duplicate_runtime_options:
                logger.warning(
                    "Found duplicate runtime options %s.",
                    duplicate_runtime_options,
                )

            runtime_options.update(component.runtime_options)

        return runtime_options

    def dict(self) -> Dict[str, str]:
        """Converts the stack into a dictionary."""
        component_dict = {
            component_type.value: component.json(sort_keys=True)
            for component_type, component in self.components.items()
        }
        component_dict.update({"name": self.name})
        return component_dict

    def requirements(
        self,
        exclude_components: Optional[AbstractSet[StackComponentType]] = None,
    ) -> Set[str]:
        """Set of PyPI requirements for the stack.

        This method combines the requirements of all stack components (except
        the ones specified in `exclude_components`).

        Args:
            exclude_components: Set of component types for which the
                requirements should not be included in the output.
        """
        exclude_components = exclude_components or set()
        requirements = [
            component.requirements
            for component in self.components.values()
            if component.type not in exclude_components
        ]
        return set.union(*requirements) if requirements else set()

    def validate(self) -> None:
        """Checks whether the stack configuration is valid.

        To check if a stack configuration is valid, the following criteria must
        be met:
        - all components must support the execution mode (either local or
         remote execution) specified by the orchestrator of the stack
        - the `StackValidator` of each stack component has to validate the
         stack to make sure all the components are compatible with each other

        Raises:
             StackValidationError: If the stack configuration is not valid.
        """

        for component in self.components.values():
            if component.validator:
                component.validator.validate(stack=self)

    def deploy_pipeline(
        self,
        pipeline: "BasePipeline",
        runtime_configuration: RuntimeConfiguration,
    ) -> Any:
        """Deploys a pipeline on this stack.

        Args:
            pipeline: The pipeline to deploy.
            runtime_configuration: Contains all the runtime configuration
                options specified for the pipeline run.

        Returns:
            The return value of the call to `orchestrator.run_pipeline(...)`.
        """
        for component in self.components.values():
            component.prepare_pipeline_deployment(
                pipeline=pipeline,
                stack=self,
                runtime_configuration=runtime_configuration,
            )

        for component in self.components.values():
            component.prepare_pipeline_run()

        runtime_configuration[
            RUN_NAME_OPTION_KEY
        ] = runtime_configuration.run_name or (
            f"{pipeline.name}-"
            f'{datetime.now().strftime("%d_%h_%y-%H_%M_%S_%f")}'
        )

        logger.info(
            "Using stack `%s` to run pipeline `%s`...",
            self.name,
            pipeline.name,
        )
        start_time = time.time()

        return_value = self.orchestrator.run_pipeline(
            pipeline, stack=self, runtime_configuration=runtime_configuration
        )

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run `%s` has finished in %s.",
            runtime_configuration.run_name,
            string_utils.get_human_readable_time(run_duration),
        )

        for component in self.components.values():
            component.cleanup_pipeline_run()

        return return_value

    @property
    def is_provisioned(self) -> bool:
        """If the stack provisioned resources to run locally."""
        return all(
            component.is_provisioned for component in self.components.values()
        )

    @property
    def is_running(self) -> bool:
        """If the stack is running locally."""
        return all(
            component.is_running for component in self.components.values()
        )

    def provision(self) -> None:
        """Provisions resources to run the stack locally.

        Raises:
            NotImplementedError: If any unprovisioned component does not
                implement provisioning.
        """
        logger.info("Provisioning resources for stack '%s'.", self.name)
        for component in self.components.values():
            if not component.is_provisioned:
                component.provision()
                logger.info("Provisioned resources for %s.", component)

    def deprovision(self) -> None:
        """Deprovisions all local resources of the stack.

        Raises:
            NotImplementedError: If any provisioned component does not
                implement deprovisioning.
        """
        logger.info("Deprovisioning resources for stack '%s'.", self.name)
        for component in self.components.values():
            if component.is_provisioned:
                try:
                    component.deprovision()
                    logger.info("Deprovisioned resources for %s.", component)
                except NotImplementedError as e:
                    logger.warning(e)

    def resume(self) -> None:
        """Resumes the provisioned local resources of the stack.

        Raises:
            ProvisioningError: If any stack component is missing provisioned
                resources.
        """
        logger.info("Resuming provisioned resources for stack %s.", self.name)
        for component in self.components.values():
            if component.is_running:
                # the component is already running, no need to resume anything
                pass
            elif component.is_provisioned:
                component.resume()
                logger.info("Resumed resources for %s.", component)
            else:
                raise ProvisioningError(
                    f"Unable to resume resources for {component}: No "
                    f"resources have been provisioned for this component."
                )

    def suspend(self) -> None:
        """Suspends the provisioned local resources of the stack."""
        logger.info(
            "Suspending provisioned resources for stack '%s'.", self.name
        )
        for component in self.components.values():
            if component.is_running:
                try:
                    component.suspend()
                    logger.info("Suspended resources for %s.", component)
                except NotImplementedError:
                    logger.warning(
                        "Suspending provisioned resources not implemented "
                        "for %s. Continuing without suspending resources...",
                        component,
                    )
