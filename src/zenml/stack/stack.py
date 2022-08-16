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
"""Implementation of the ZenML Stack class."""

import os
import time
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
from zenml.constants import (
    ENV_ZENML_SECRET_VALIDATION_LEVEL,
    ZENML_IGNORE_STORE_COUPLINGS,
)
from zenml.enums import SecretValidationLevel, StackComponentType
from zenml.exceptions import ProvisioningError, StackValidationError
from zenml.logger import get_logger
from zenml.runtime_configuration import (
    RUN_NAME_OPTION_KEY,
    RuntimeConfiguration,
)
from zenml.utils import io_utils, string_utils

if TYPE_CHECKING:
    from zenml.alerter import BaseAlerter
    from zenml.annotators import BaseAnnotator
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.container_registries import BaseContainerRegistry
    from zenml.data_validators import BaseDataValidator
    from zenml.experiment_trackers.base_experiment_tracker import (
        BaseExperimentTracker,
    )
    from zenml.feature_stores import BaseFeatureStore
    from zenml.metadata_stores import BaseMetadataStore
    from zenml.model_deployers import BaseModelDeployer
    from zenml.orchestrators import BaseOrchestrator
    from zenml.pipelines import BasePipeline
    from zenml.secrets_managers import BaseSecretsManager
    from zenml.stack import StackComponent
    from zenml.step_operators import BaseStepOperator
    from zenml.utils import secret_utils


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
        feature_store: Optional["BaseFeatureStore"] = None,
        model_deployer: Optional["BaseModelDeployer"] = None,
        experiment_tracker: Optional["BaseExperimentTracker"] = None,
        alerter: Optional["BaseAlerter"] = None,
        annotator: Optional["BaseAnnotator"] = None,
        data_validator: Optional["BaseDataValidator"] = None,
    ):
        """Initializes and validates a stack instance.

        # noqa: DAR402

        Args:
            name: Name of the stack.
            orchestrator: Orchestrator component of the stack.
            metadata_store: Metadata store component of the stack.
            artifact_store: Artifact store component of the stack.
            container_registry: Container registry component of the stack.
            secrets_manager: Secrets manager component of the stack.
            step_operator: Step operator component of the stack.
            feature_store: Feature store component of the stack.
            model_deployer: Model deployer component of the stack.
            experiment_tracker: Experiment tracker component of the stack.
            alerter: Alerter component of the stack.
            annotator: Annotator component of the stack.
            data_validator: Data validator component of the stack.

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
        self._feature_store = feature_store
        self._model_deployer = model_deployer
        self._experiment_tracker = experiment_tracker
        self._alerter = alerter
        self._annotator = annotator
        self._data_validator = data_validator

    @classmethod
    def from_components(
        cls, name: str, components: Dict[StackComponentType, "StackComponent"]
    ) -> "Stack":
        """Creates a stack instance from a dict of stack components.

        # noqa: DAR402

        Args:
            name: The name of the stack.
            components: The components of the stack.

        Returns:
            A stack instance consisting of the given components.

        Raises:
            TypeError: If a required component is missing or a component
                doesn't inherit from the expected base class.
        """
        from zenml.alerter import BaseAlerter
        from zenml.annotators import BaseAnnotator
        from zenml.artifact_stores import BaseArtifactStore
        from zenml.container_registries import BaseContainerRegistry
        from zenml.data_validators import BaseDataValidator
        from zenml.experiment_trackers import BaseExperimentTracker
        from zenml.feature_stores import BaseFeatureStore
        from zenml.metadata_stores import BaseMetadataStore
        from zenml.model_deployers import BaseModelDeployer
        from zenml.orchestrators import BaseOrchestrator
        from zenml.secrets_managers import BaseSecretsManager
        from zenml.step_operators import BaseStepOperator

        def _raise_type_error(
            component: Optional["StackComponent"], expected_class: Type[Any]
        ) -> NoReturn:
            """Raises a TypeError that the component has an unexpected type.

            Args:
                component: The component that has an unexpected type.
                expected_class: The expected type of the component.

            Raises:
                TypeError: If the component has an unexpected type.
            """
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

        feature_store = components.get(StackComponentType.FEATURE_STORE)
        if feature_store is not None and not isinstance(
            feature_store, BaseFeatureStore
        ):
            _raise_type_error(feature_store, BaseFeatureStore)

        model_deployer = components.get(StackComponentType.MODEL_DEPLOYER)
        if model_deployer is not None and not isinstance(
            model_deployer, BaseModelDeployer
        ):
            _raise_type_error(model_deployer, BaseModelDeployer)

        experiment_tracker = components.get(
            StackComponentType.EXPERIMENT_TRACKER
        )
        if experiment_tracker is not None and not isinstance(
            experiment_tracker, BaseExperimentTracker
        ):
            _raise_type_error(experiment_tracker, BaseExperimentTracker)

        alerter = components.get(StackComponentType.ALERTER)
        if alerter is not None and not isinstance(alerter, BaseAlerter):
            _raise_type_error(alerter, BaseAlerter)

        annotator = components.get(StackComponentType.ANNOTATOR)
        if annotator is not None and not isinstance(annotator, BaseAnnotator):
            _raise_type_error(annotator, BaseAnnotator)

        data_validator = components.get(StackComponentType.DATA_VALIDATOR)
        if data_validator is not None and not isinstance(
            data_validator, BaseDataValidator
        ):
            _raise_type_error(data_validator, BaseDataValidator)

        return Stack(
            name=name,
            orchestrator=orchestrator,
            metadata_store=metadata_store,
            artifact_store=artifact_store,
            container_registry=container_registry,
            secrets_manager=secrets_manager,
            step_operator=step_operator,
            feature_store=feature_store,
            model_deployer=model_deployer,
            experiment_tracker=experiment_tracker,
            alerter=alerter,
            annotator=annotator,
            data_validator=data_validator,
        )

    @classmethod
    def default_local_stack(cls) -> "Stack":
        """Creates a stack instance which is configured to run locally.

        Returns:
            A stack instance configured to run locally.
        """
        from zenml.artifact_stores import LocalArtifactStore
        from zenml.metadata_stores import SQLiteMetadataStore
        from zenml.orchestrators import LocalOrchestrator
        from zenml.stack.stack_component import uuid_factory

        orchestrator = LocalOrchestrator(name="default")

        artifact_store_uuid = uuid_factory()
        artifact_store_path = os.path.join(
            GlobalConfiguration().config_directory,
            "local_stores",
            str(artifact_store_uuid),
        )
        io_utils.create_dir_recursive_if_not_exists(artifact_store_path)
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
        """All components of the stack.

        Returns:
            A dictionary of all components of the stack.
        """
        return {
            component.TYPE: component
            for component in [
                self.orchestrator,
                self.metadata_store,
                self.artifact_store,
                self.container_registry,
                self.secrets_manager,
                self.step_operator,
                self.feature_store,
                self.model_deployer,
                self.experiment_tracker,
                self.alerter,
                self.annotator,
                self.data_validator,
            ]
            if component is not None
        }

    @property
    def name(self) -> str:
        """The name of the stack.

        Returns:
            str: The name of the stack.
        """
        return self._name

    @property
    def orchestrator(self) -> "BaseOrchestrator":
        """The orchestrator of the stack.

        Returns:
            The orchestrator of the stack.
        """
        return self._orchestrator

    @property
    def metadata_store(self) -> "BaseMetadataStore":
        """The metadata store of the stack.

        Returns:
            The metadata store of the stack.
        """
        return self._metadata_store

    @property
    def artifact_store(self) -> "BaseArtifactStore":
        """The artifact store of the stack.

        Returns:
            The artifact store of the stack.
        """
        return self._artifact_store

    @property
    def container_registry(self) -> Optional["BaseContainerRegistry"]:
        """The container registry of the stack.

        Returns:
            The container registry of the stack or None if the stack does not
            have a container registry.
        """
        return self._container_registry

    @property
    def secrets_manager(self) -> Optional["BaseSecretsManager"]:
        """The secrets manager of the stack.

        Returns:
            The secrets manager of the stack.
        """
        return self._secrets_manager

    @property
    def step_operator(self) -> Optional["BaseStepOperator"]:
        """The step operator of the stack.

        Returns:
            The step operator of the stack.
        """
        return self._step_operator

    @property
    def feature_store(self) -> Optional["BaseFeatureStore"]:
        """The feature store of the stack.

        Returns:
            The feature store of the stack.
        """
        return self._feature_store

    @property
    def model_deployer(self) -> Optional["BaseModelDeployer"]:
        """The model deployer of the stack.

        Returns:
            The model deployer of the stack.
        """
        return self._model_deployer

    @property
    def experiment_tracker(self) -> Optional["BaseExperimentTracker"]:
        """The experiment tracker of the stack.

        Returns:
            The experiment tracker of the stack.
        """
        return self._experiment_tracker

    @property
    def alerter(self) -> Optional["BaseAlerter"]:
        """The alerter of the stack.

        Returns:
            The alerter of the stack.
        """
        return self._alerter

    @property
    def annotator(self) -> Optional["BaseAnnotator"]:
        """The annotator of the stack.

        Returns:
            The annotator of the stack.
        """
        return self._annotator

    @property
    def data_validator(self) -> Optional["BaseDataValidator"]:
        """The data validator of the stack.

        Returns:
            The data validator of the stack.
        """
        return self._data_validator

    @property
    def runtime_options(self) -> Dict[str, Any]:
        """Runtime options that are available to configure this stack.

        This method combines the available runtime options for all components
        of this stack. See `StackComponent.runtime_options()` for
        more information.

        Returns:
            A dictionary of runtime options.
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
        """Converts the stack into a dictionary.

        Returns:
            A dictionary containing the stack components.
        """
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

        Returns:
            Set of PyPI requirements.
        """
        exclude_components = exclude_components or set()
        requirements = [
            component.requirements
            for component in self.components.values()
            if component.TYPE not in exclude_components
        ]
        return set.union(*requirements) if requirements else set()

    @property
    def required_secrets(self) -> Set["secret_utils.SecretReference"]:
        """All required secrets for this stack.

        Returns:
            The required secrets of this stack.
        """
        secrets = [
            component.required_secrets for component in self.components.values()
        ]
        return set.union(*secrets) if secrets else set()

    def _validate_secrets(self, raise_exception: bool) -> None:
        """Validates that all secrets of the stack exists.

        Args:
            raise_exception: If `True`, raises an exception if the stack has
                no secrets manager or a secret is missing. Otherwise a
                warning is logged.

        # noqa: DAR402
        Raises:
            StackValidationError: If the stack has no secrets manager or a
                secret is missing.
        """
        env_value = os.getenv(
            ENV_ZENML_SECRET_VALIDATION_LEVEL,
            default=SecretValidationLevel.SECRET_AND_KEY_EXISTS.value,
        )
        secret_validation_level = SecretValidationLevel(env_value)

        required_secrets = self.required_secrets
        if (
            secret_validation_level != SecretValidationLevel.NONE
            and required_secrets
        ):

            def _handle_error(message: str) -> None:
                """Handles the error by raising an exception or logging.

                Args:
                    message: The error message.

                Raises:
                    StackValidationError: If called and `raise_exception` of
                        the outer method is `True`.
                """
                if raise_exception:
                    raise StackValidationError(message)
                else:
                    message += (
                        "\nYou need to solve this issue before running "
                        "a pipeline on this stack."
                    )
                    logger.warning(message)

            if not self.secrets_manager:
                _handle_error(
                    f"Some component in stack `{self.name}` reference secret "
                    "values, but there is no secrets manager in this stack."
                )
                return

            missing = []
            existing_secrets = set(self.secrets_manager.get_all_secret_keys())
            for secret_ref in required_secrets:
                if (
                    secret_validation_level
                    == SecretValidationLevel.SECRET_AND_KEY_EXISTS
                ):
                    try:
                        _ = self.secrets_manager.get_secret(
                            secret_ref.name
                        ).content[secret_ref.key]
                    except KeyError:
                        missing.append(secret_ref)
                elif (
                    secret_validation_level
                    == SecretValidationLevel.SECRET_EXISTS
                ):
                    if secret_ref.name not in existing_secrets:
                        missing.append(secret_ref)

            if missing:
                _handle_error(
                    f"Missing secrets for stack: {missing}.\nTo register the "
                    "missing secrets for this stack, run `zenml stack "
                    f"register-secrets {self.name}`\nIf you want to "
                    "adjust the degree to which ZenML validates the existence "
                    "of secrets in your stack, you can do so by setting the "
                    f"environment variable {ENV_ZENML_SECRET_VALIDATION_LEVEL} "
                    "to one of the following values: "
                    f"{SecretValidationLevel.values()}."
                )

    def validate(
        self,
        decouple_stores: bool = False,
        fail_if_secrets_missing: bool = False,
    ) -> None:
        """Checks whether the stack configuration is valid.

        To check if a stack configuration is valid, the following criteria must
        be met:
        - the `StackValidator` of each stack component has to validate the
            stack to make sure all the components are compatible with each other
        - the stack must either have a properly associated artifact/metadata
            store pair or reset the association.
        - the required secrets of all components need to exist

        Args:
            decouple_stores: Flag to reset the previous associations between
                an artifact store and a metadata store
            fail_if_secrets_missing: If this is `True`, an error will be raised
                if a secret for a component is missing. Otherwise, only a
                warning will be logged.

        Raises:
            StackValidationError: If the artifact store and the metadata store
                are not properly associated.
        """
        for component in self.components.values():
            if component.validator:
                component.validator.validate(stack=self)

        self._validate_secrets(raise_exception=fail_if_secrets_missing)

        if not ZENML_IGNORE_STORE_COUPLINGS:
            from zenml.cli.utils import warning
            from zenml.repository import Repository

            repo = Repository()
            artifact_store_associations = (
                repo.zen_store.get_store_associations_for_artifact_store(
                    self.artifact_store.uuid
                )
            )
            if artifact_store_associations:
                for association in artifact_store_associations:
                    if (
                        association.metadata_store_uuid
                        != self.metadata_store.uuid
                    ):
                        if decouple_stores:
                            warning(
                                f"Removing the association between given "
                                f"artifact store {self.artifact_store.name} "
                                f"(uuid: {self.artifact_store.uuid}) and the "
                                f"metadata store (uuid: "
                                f"{association.metadata_store_uuid})."
                            )
                            repo.zen_store.delete_store_association_for_artifact_and_metadata_store(
                                artifact_store_uuid=self.artifact_store.uuid,
                                metadata_store_uuid=association.metadata_store_uuid,
                            )
                        else:
                            raise StackValidationError(
                                f"The artifact store instance in your stack "
                                f"'{self.artifact_store.name}' (uuid: "
                                f"{self.artifact_store.uuid}) has been "
                                f"previously associated with a different "
                                f"metadata store (uuid: "
                                f"{association.metadata_store_uuid} in a "
                                f"different stack. If either one of these "
                                f"stores are previously populated, this might "
                                f"lead to various problems. In order to solve "
                                f"this issue, you can either create and use "
                                f"another artifact store instance or use the "
                                f"'--decouple_stores' flag when you register/update a stack "
                                f"to reset the associations of these "
                                f"components."
                            )

            m_associations = (
                repo.zen_store.get_store_associations_for_metadata_store(
                    self.metadata_store.uuid
                )
            )
            if m_associations:
                for association in m_associations:
                    if (
                        association.artifact_store_uuid
                        != self.artifact_store.uuid
                    ):
                        if decouple_stores:
                            warning(
                                f"Removing the association between given "
                                f"metadata store {self.metadata_store.name} "
                                f"(uuid: {self.metadata_store.uuid}) and the "
                                f"artifact store (uuid: "
                                f"{association.artifact_store_uuid})."
                            )
                            repo.zen_store.delete_store_association_for_artifact_and_metadata_store(
                                artifact_store_uuid=association.artifact_store_uuid,
                                metadata_store_uuid=self.metadata_store.uuid,
                            )
                        else:
                            raise StackValidationError(
                                f"The metadata store instance in your stack "
                                f"'{self.metadata_store.name}' (uuid: "
                                f"{self.metadata_store.uuid}) has been "
                                f"previously associated with a different "
                                f"artifact store (uuid: "
                                f"{association.artifact_store_uuid} in a "
                                f"different stack. If either one of these "
                                f"stores are previously populated, this might "
                                f"lead to various problems. In order to solve "
                                f"this issue, you can either create and use "
                                f"another artifact store instance or use the "
                                f"'--decouple_stores' flag when you register/update a stack "
                                f"to reset the associations of these "
                                f"components."
                            )

            # Check if the associations already exists, if not create it
            existing_associations = repo.zen_store.get_store_associations_for_artifact_and_metadata_store(
                artifact_store_uuid=self.artifact_store.uuid,
                metadata_store_uuid=self.metadata_store.uuid,
            )
            if len(existing_associations) == 0:
                repo.zen_store.create_store_association(
                    artifact_store_uuid=self.artifact_store.uuid,
                    metadata_store_uuid=self.metadata_store.uuid,
                )

    def _register_pipeline_run(
        self,
        pipeline: "BasePipeline",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Registers a pipeline run in the ZenStore.

        Args:
            pipeline: The pipeline that is being run.
            runtime_configuration: The runtime configuration of the pipeline.
        """
        from zenml.repository import Repository
        from zenml.zen_stores.models import StackWrapper
        from zenml.zen_stores.models.pipeline_models import (
            PipelineRunWrapper,
            PipelineWrapper,
        )

        repo = Repository()
        active_project = repo.active_project
        pipeline_run_wrapper = PipelineRunWrapper(
            name=runtime_configuration.run_name,
            pipeline=PipelineWrapper.from_pipeline(pipeline),
            stack=StackWrapper.from_stack(self),
            runtime_configuration=runtime_configuration,
            user_id=repo.active_user.id,
            project_name=active_project.name if active_project else None,
        )

        Repository().zen_store.register_pipeline_run(pipeline_run_wrapper)

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

        Raises:
            StackValidationError: If the stack configuration is not valid.
        """
        self.validate(fail_if_secrets_missing=True)

        for component in self.components.values():
            if not component.is_running:
                raise StackValidationError(
                    f"The '{component.name}' {component.TYPE} stack component "
                    f"is not currently running. Please run the following "
                    f"command to provision and start the component:\n\n"
                    f"    `zenml stack up`\n"
                )

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

        original_cache_boolean = pipeline.enable_cache
        if "enable_cache" in runtime_configuration:
            logger.info(
                "Runtime configuration overwriting the pipeline cache settings"
                " to enable_cache=`%s` for this pipeline run. The default "
                "caching strategy is retained for future pipeline runs.",
                runtime_configuration["enable_cache"],
            )
            pipeline.enable_cache = runtime_configuration.get("enable_cache")

        self._register_pipeline_run(
            pipeline=pipeline, runtime_configuration=runtime_configuration
        )

        return_value = self.orchestrator.run(
            pipeline, stack=self, runtime_configuration=runtime_configuration
        )

        # Put pipeline level cache policy back to make sure the next runs
        #  default to that policy again in case the runtime configuration
        #  is not set explicitly
        pipeline.enable_cache = original_cache_boolean

        run_duration = time.time() - start_time
        logger.info(
            "Pipeline run `%s` has finished in %s.",
            runtime_configuration.run_name,
            string_utils.get_human_readable_time(run_duration),
        )

        for component in self.components.values():
            component.cleanup_pipeline_run()

        return return_value

    def prepare_step_run(self) -> None:
        """Prepares running a step."""
        for component in self.components.values():
            component.prepare_step_run()

    def cleanup_step_run(self) -> None:
        """Cleans up resources after the step run is finished."""
        for component in self.components.values():
            component.cleanup_step_run()

    @property
    def is_provisioned(self) -> bool:
        """If the stack provisioned resources to run locally.

        Returns:
            True if the stack provisioned resources to run locally.
        """
        return all(
            component.is_provisioned for component in self.components.values()
        )

    @property
    def is_running(self) -> bool:
        """If the stack is running locally.

        Returns:
            True if the stack is running locally, False otherwise.
        """
        return all(
            component.is_running for component in self.components.values()
        )

    def provision(self) -> None:
        """Provisions resources to run the stack locally."""
        logger.info("Provisioning resources for stack '%s'.", self.name)
        for component in self.components.values():
            if not component.is_provisioned:
                component.provision()
                logger.info("Provisioned resources for %s.", component)

    def deprovision(self) -> None:
        """Deprovisions all local resources of the stack."""
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
            if not component.is_suspended:
                try:
                    component.suspend()
                    logger.info("Suspended resources for %s.", component)
                except NotImplementedError:
                    logger.warning(
                        "Suspending provisioned resources not implemented "
                        "for %s. Continuing without suspending resources...",
                        component,
                    )
