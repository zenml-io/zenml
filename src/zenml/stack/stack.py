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

import itertools
import json
import os
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Any,
    Dict,
    List,
    NoReturn,
    Optional,
    Set,
    Tuple,
    Type,
)
from uuid import UUID

from zenml.client import Client
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_SECRET_VALIDATION_LEVEL,
    ENV_ZENML_SKIP_IMAGE_BUILDER_DEFAULT,
    handle_bool_env_var,
)
from zenml.enums import SecretValidationLevel, StackComponentType
from zenml.exceptions import ProvisioningError, StackValidationError
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models import StackResponse
from zenml.utils import pagination_utils, settings_utils

if TYPE_CHECKING:
    from zenml.alerter import BaseAlerter
    from zenml.annotators import BaseAnnotator
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_configurations import StepConfiguration
    from zenml.config.step_run_info import StepRunInfo
    from zenml.container_registries import BaseContainerRegistry
    from zenml.data_validators import BaseDataValidator
    from zenml.experiment_trackers.base_experiment_tracker import (
        BaseExperimentTracker,
    )
    from zenml.feature_stores import BaseFeatureStore
    from zenml.image_builders import BaseImageBuilder
    from zenml.model_deployers import BaseModelDeployer
    from zenml.model_registries import BaseModelRegistry
    from zenml.models import (
        PipelineDeploymentBase,
        PipelineDeploymentResponse,
        PipelineRunResponse,
    )
    from zenml.orchestrators import BaseOrchestrator
    from zenml.stack import StackComponent
    from zenml.step_operators import BaseStepOperator
    from zenml.utils import secret_utils


logger = get_logger(__name__)

_STACK_CACHE: Dict[Tuple[UUID, Optional[datetime]], "Stack"] = {}


class Stack:
    """ZenML stack class.

    A ZenML stack is a collection of multiple stack components that are
    required to run ZenML pipelines. Some of these components (orchestrator,
    and artifact store) are required to run any kind of
    pipeline, other components like the container registry are only required
    if other stack components depend on them.
    """

    def __init__(
        self,
        id: UUID,
        name: str,
        *,
        orchestrator: "BaseOrchestrator",
        artifact_store: "BaseArtifactStore",
        container_registry: Optional["BaseContainerRegistry"] = None,
        step_operator: Optional["BaseStepOperator"] = None,
        feature_store: Optional["BaseFeatureStore"] = None,
        model_deployer: Optional["BaseModelDeployer"] = None,
        experiment_tracker: Optional["BaseExperimentTracker"] = None,
        alerter: Optional["BaseAlerter"] = None,
        annotator: Optional["BaseAnnotator"] = None,
        data_validator: Optional["BaseDataValidator"] = None,
        image_builder: Optional["BaseImageBuilder"] = None,
        model_registry: Optional["BaseModelRegistry"] = None,
    ):
        """Initializes and validates a stack instance.

        Args:
            id: Unique ID of the stack.
            name: Name of the stack.
            orchestrator: Orchestrator component of the stack.
            artifact_store: Artifact store component of the stack.
            container_registry: Container registry component of the stack.
            step_operator: Step operator component of the stack.
            feature_store: Feature store component of the stack.
            model_deployer: Model deployer component of the stack.
            experiment_tracker: Experiment tracker component of the stack.
            alerter: Alerter component of the stack.
            annotator: Annotator component of the stack.
            data_validator: Data validator component of the stack.
            image_builder: Image builder component of the stack.
            model_registry: Model registry component of the stack.
        """
        self._id = id
        self._name = name
        self._orchestrator = orchestrator
        self._artifact_store = artifact_store
        self._container_registry = container_registry
        self._step_operator = step_operator
        self._feature_store = feature_store
        self._model_deployer = model_deployer
        self._experiment_tracker = experiment_tracker
        self._alerter = alerter
        self._annotator = annotator
        self._data_validator = data_validator
        self._model_registry = model_registry
        self._image_builder = image_builder

    @classmethod
    def from_model(cls, stack_model: "StackResponse") -> "Stack":
        """Creates a Stack instance from a StackModel.

        Args:
            stack_model: The StackModel to create the Stack from.

        Returns:
            The created Stack instance.
        """
        global _STACK_CACHE
        key = (stack_model.id, stack_model.updated)
        if key in _STACK_CACHE:
            return _STACK_CACHE[key]

        from zenml.stack import StackComponent

        # Run a hydrated list call once to avoid one request per component
        component_models = pagination_utils.depaginate(
            Client().list_stack_components,
            stack_id=stack_model.id,
            hydrate=True,
        )

        stack_components = {
            model.type: StackComponent.from_model(model)
            for model in component_models
        }
        stack = Stack.from_components(
            id=stack_model.id,
            name=stack_model.name,
            components=stack_components,
        )
        _STACK_CACHE[key] = stack

        client = Client()
        if stack_model.id == client.active_stack_model.id:
            if stack_model.updated > client.active_stack_model.updated:
                if client._config:
                    client._config.set_active_stack(stack_model)
                else:
                    GlobalConfiguration().set_active_stack(stack_model)

        return stack

    @classmethod
    def from_components(
        cls,
        id: UUID,
        name: str,
        components: Dict[StackComponentType, "StackComponent"],
    ) -> "Stack":
        """Creates a stack instance from a dict of stack components.

        # noqa: DAR402

        Args:
            id: Unique ID of the stack.
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
        from zenml.image_builders import BaseImageBuilder
        from zenml.model_deployers import BaseModelDeployer
        from zenml.model_registries import BaseModelRegistry
        from zenml.orchestrators import BaseOrchestrator
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

        image_builder = components.get(StackComponentType.IMAGE_BUILDER)
        if image_builder is not None and not isinstance(
            image_builder, BaseImageBuilder
        ):
            _raise_type_error(image_builder, BaseImageBuilder)

        model_registry = components.get(StackComponentType.MODEL_REGISTRY)
        if model_registry is not None and not isinstance(
            model_registry, BaseModelRegistry
        ):
            _raise_type_error(model_registry, BaseModelRegistry)

        return Stack(
            id=id,
            name=name,
            orchestrator=orchestrator,
            artifact_store=artifact_store,
            container_registry=container_registry,
            step_operator=step_operator,
            feature_store=feature_store,
            model_deployer=model_deployer,
            experiment_tracker=experiment_tracker,
            alerter=alerter,
            annotator=annotator,
            data_validator=data_validator,
            image_builder=image_builder,
            model_registry=model_registry,
        )

    @property
    def components(self) -> Dict[StackComponentType, "StackComponent"]:
        """All components of the stack.

        Returns:
            A dictionary of all components of the stack.
        """
        return {
            component.type: component
            for component in [
                self.orchestrator,
                self.artifact_store,
                self.container_registry,
                self.step_operator,
                self.feature_store,
                self.model_deployer,
                self.experiment_tracker,
                self.alerter,
                self.annotator,
                self.data_validator,
                self.image_builder,
                self.model_registry,
            ]
            if component is not None
        }

    @property
    def id(self) -> UUID:
        """The ID of the stack.

        Returns:
            The ID of the stack.
        """
        return self._id

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
    def image_builder(self) -> Optional["BaseImageBuilder"]:
        """The image builder of the stack.

        Returns:
            The image builder of the stack.
        """
        return self._image_builder

    @property
    def model_registry(self) -> Optional["BaseModelRegistry"]:
        """The model registry of the stack.

        Returns:
            The model registry of the stack.
        """
        return self._model_registry

    def dict(self) -> Dict[str, str]:
        """Converts the stack into a dictionary.

        Returns:
            A dictionary containing the stack components.
        """
        component_dict = {
            component_type.value: json.dumps(
                component.config.model_dump(mode="json"), sort_keys=True
            )
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
            if component.type not in exclude_components
        ]
        return set.union(*requirements) if requirements else set()

    @property
    def apt_packages(self) -> List[str]:
        """List of APT package requirements for the stack.

        Returns:
            A list of APT package requirements for the stack.
        """
        return [
            package
            for component in self.components.values()
            for package in component.apt_packages
        ]

    def check_local_paths(self) -> bool:
        """Checks if the stack has local paths.

        Returns:
            True if the stack has local paths, False otherwise.

        Raises:
            ValueError: If the stack has local paths that do not conform to
                the convention that all local path must be relative to the
                local stores directory.
        """
        from zenml.config.global_config import GlobalConfiguration

        local_stores_path = GlobalConfiguration().local_stores_path

        # go through all stack components and identify those that advertise
        # a local path where they persist information that they need to be
        # available when running pipelines.
        has_local_paths = False
        for stack_comp in self.components.values():
            local_path = stack_comp.local_path
            if not local_path:
                continue
            # double-check this convention, just in case it wasn't respected
            # as documented in `StackComponent.local_path`
            if not local_path.startswith(local_stores_path):
                raise ValueError(
                    f"Local path {local_path} for component "
                    f"{stack_comp.name} is not in the local stores "
                    f"directory ({local_stores_path})."
                )
            has_local_paths = True

        return has_local_paths

    @property
    def required_secrets(self) -> Set["secret_utils.SecretReference"]:
        """All required secrets for this stack.

        Returns:
            The required secrets of this stack.
        """
        secrets = [
            component.config.required_secrets
            for component in self.components.values()
        ]
        return set.union(*secrets) if secrets else set()

    @property
    def setting_classes(self) -> Dict[str, Type["BaseSettings"]]:
        """Setting classes of all components of this stack.

        Returns:
            All setting classes and their respective keys.
        """
        setting_classes = {}
        for component in self.components.values():
            if component.settings_class:
                key = settings_utils.get_stack_component_setting_key(component)
                setting_classes[key] = component.settings_class
        return setting_classes

    @property
    def requires_remote_server(self) -> bool:
        """If the stack requires a remote ZenServer to run.

        This is the case if any code is getting executed remotely. This is the
        case for both remote orchestrators as well as remote step operators.

        Returns:
            If the stack requires a remote ZenServer to run.
        """
        return self.orchestrator.config.is_remote or (
            self.step_operator is not None
            and self.step_operator.config.is_remote
        )

    def _validate_secrets(self, raise_exception: bool) -> None:
        """Validates that all secrets of the stack exists.

        Args:
            raise_exception: If `True`, raises an exception if a secret is
                missing. Otherwise a warning is logged.

        # noqa: DAR402
        Raises:
            StackValidationError: If a secret is missing.
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

            client = Client()

            # Attempt to resolve secrets through the secrets store
            for secret_ref in required_secrets.copy():
                try:
                    secret = client.get_secret(secret_ref.name)
                    if (
                        secret_validation_level
                        == SecretValidationLevel.SECRET_AND_KEY_EXISTS
                    ):
                        _ = secret.values[secret_ref.key]
                except (KeyError, NotImplementedError):
                    pass
                else:
                    # Drop this secret from the list of required secrets
                    required_secrets.remove(secret_ref)

            if not required_secrets:
                return

            secrets_msg = ", ".join(
                [
                    f"{secret_ref.name}.{secret_ref.key}"
                    for secret_ref in required_secrets
                ]
            )

            _handle_error(
                f"Some components in the `{self.name}` stack reference secrets "
                f"or secret keys that do not exist in the secret store: "
                f"{secrets_msg}.\nTo register the "
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
        fail_if_secrets_missing: bool = False,
    ) -> None:
        """Checks whether the stack configuration is valid.

        To check if a stack configuration is valid, the following criteria must
        be met:
        - the stack must have an image builder if other components require it
        - the `StackValidator` of each stack component has to validate the
            stack to make sure all the components are compatible with each other
        - the required secrets of all components need to exist

        Args:
            fail_if_secrets_missing: If this is `True`, an error will be raised
                if a secret for a component is missing. Otherwise, only a
                warning will be logged.
        """
        self.validate_image_builder()
        for component in self.components.values():
            if component.validator:
                component.validator.validate(stack=self)

        self._validate_secrets(raise_exception=fail_if_secrets_missing)

    def validate_image_builder(self) -> None:
        """Validates that the stack has an image builder if required.

        If the stack requires an image builder, but none is specified, a
        local image builder will be created and assigned to the stack to
        ensure backwards compatibility.
        """
        requires_image_builder = (
            self.orchestrator.flavor != "local"
            or self.step_operator
            or (self.model_deployer and self.model_deployer.flavor != "mlflow")
        )
        skip_default_image_builder = handle_bool_env_var(
            ENV_ZENML_SKIP_IMAGE_BUILDER_DEFAULT, default=False
        )
        if (
            requires_image_builder
            and not skip_default_image_builder
            and not self.image_builder
        ):
            from datetime import datetime
            from uuid import uuid4

            from zenml.image_builders import (
                LocalImageBuilder,
                LocalImageBuilderConfig,
                LocalImageBuilderFlavor,
            )

            flavor = LocalImageBuilderFlavor()

            image_builder = LocalImageBuilder(
                id=uuid4(),
                name="temporary_default",
                flavor=flavor.name,
                type=flavor.type,
                config=LocalImageBuilderConfig(),
                user=Client().active_user.id,
                workspace=Client().active_workspace.id,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )

            logger.warning(
                "The stack `%s` contains components that require building "
                "Docker images. Older versions of ZenML always built these "
                "images locally, but since version 0.32.0 this behavior can be "
                "configured using the `image_builder` stack component. This "
                "stack will temporarily default to a local image builder that "
                "mirrors the previous behavior, but this will be removed in "
                "future versions of ZenML. Please add an image builder to this "
                "stack:\n"
                "`zenml image-builder register <NAME> ...\n"
                "zenml stack update %s -i <NAME>`",
                self.name,
                self.id,
            )

            self._image_builder = image_builder

    def prepare_pipeline_deployment(
        self, deployment: "PipelineDeploymentResponse"
    ) -> None:
        """Prepares the stack for a pipeline deployment.

        This method is called before a pipeline is deployed.

        Args:
            deployment: The pipeline deployment

        Raises:
            StackValidationError: If the stack component is not running.
            RuntimeError: If trying to deploy a pipeline that requires a remote
                ZenML server with a local one.
        """
        self.validate(fail_if_secrets_missing=True)

        for component in self.components.values():
            if not component.is_running:
                raise StackValidationError(
                    f"The '{component.name}' {component.type} stack component "
                    f"is not currently running. Please run the following "
                    f"command to provision and start the component:\n\n"
                    f"    `zenml stack up`\n"
                    f"It is worth noting that the provision command will "
                    f" be deprecated in the future. ZenML will no longer "
                    f"be responsible for provisioning infrastructure, "
                    f"or port-forwarding directly. Instead of managing "
                    f"the state of the components, ZenML will be utilizing "
                    f"the already running stack or stack components directly. "
                    f"Additionally, we are also providing a variety of "
                    f" deployment recipes for popular Kubernetes-based "
                    f"integrations such as Kubeflow, Tekton, and Seldon etc."
                    f"Check out https://docs.zenml.io/how-to/stack-deployment/deploy-a-stack-using-mlstacks"
                    f"for more information."
                )

        if self.requires_remote_server and Client().zen_store.is_local_store():
            raise RuntimeError(
                "Stacks with remote components such as remote orchestrators "
                "and step operators require a remote "
                "ZenML server. To run a pipeline with this stack you need to "
                "connect to a remote ZenML server first. Check out "
                "https://docs.zenml.io/getting-started/deploying-zenml "
                "for more information on how to deploy ZenML."
            )

        for component in self.components.values():
            component.prepare_pipeline_deployment(
                deployment=deployment, stack=self
            )

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the stack.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        return list(
            itertools.chain.from_iterable(
                component.get_docker_builds(deployment=deployment)
                for component in self.components.values()
            )
        )

    def deploy_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Any:
        """Deploys a pipeline on this stack.

        Args:
            deployment: The pipeline deployment.
            placeholder_run: An optional placeholder run for the deployment.
                This will be deleted in case the pipeline deployment failed.

        Returns:
            The return value of the call to `orchestrator.run_pipeline(...)`.
        """
        return self.orchestrator.run(
            deployment=deployment, stack=self, placeholder_run=placeholder_run
        )

    def _get_active_components_for_step(
        self, step_config: "StepConfiguration"
    ) -> Dict[StackComponentType, "StackComponent"]:
        """Gets all the active stack components for a stack.

        Args:
            step_config: Configuration of the step for which to get the active
                components.

        Returns:
            Dictionary of active stack components.
        """

        def _is_active(component: "StackComponent") -> bool:
            """Checks whether a stack component is actively used in the step.

            Args:
                component: The component to check.

            Returns:
                If the component is used in this step.
            """
            if component.type == StackComponentType.STEP_OPERATOR:
                return component.name == step_config.step_operator

            if component.type == StackComponentType.EXPERIMENT_TRACKER:
                return component.name == step_config.experiment_tracker

            return True

        return {
            component_type: component
            for component_type, component in self.components.items()
            if _is_active(component)
        }

    def prepare_step_run(self, info: "StepRunInfo") -> None:
        """Prepares running a step.

        Args:
            info: Info about the step that will be executed.
        """
        for component in self._get_active_components_for_step(
            info.config
        ).values():
            component.prepare_step_run(info=info)

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[UUID, Dict[str, MetadataType]]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: ID of the pipeline run.

        Returns:
            A dictionary mapping component IDs to the metadata they created.
        """
        pipeline_run_metadata: Dict[UUID, Dict[str, MetadataType]] = {}
        for component in self.components.values():
            try:
                component_metadata = component.get_pipeline_run_metadata(
                    run_id=run_id
                )
                if component_metadata:
                    pipeline_run_metadata[component.id] = component_metadata
            except Exception as e:
                logger.warning(
                    f"Extracting pipeline run metadata failed for component "
                    f"'{component.name}' of type '{component.type}': {e}"
                )
        return pipeline_run_metadata

    def get_step_run_metadata(
        self, info: "StepRunInfo"
    ) -> Dict[UUID, Dict[str, MetadataType]]:
        """Get component-specific metadata for a step run.

        Args:
            info: Info about the step that was executed.

        Returns:
            A dictionary mapping component IDs to the metadata they created.
        """
        step_run_metadata: Dict[UUID, Dict[str, MetadataType]] = {}
        for component in self._get_active_components_for_step(
            info.config
        ).values():
            try:
                component_metadata = component.get_step_run_metadata(info=info)
                if component_metadata:
                    step_run_metadata[component.id] = component_metadata
            except Exception as e:
                logger.warning(
                    f"Extracting step run metadata failed for component "
                    f"'{component.name}' of type '{component.type}': {e}"
                )
        return step_run_metadata

    def cleanup_step_run(self, info: "StepRunInfo", step_failed: bool) -> None:
        """Cleans up resources after the step run is finished.

        Args:
            info: Info about the step that was executed.
            step_failed: Whether the step failed.
        """
        for component in self._get_active_components_for_step(
            info.config
        ).values():
            component.cleanup_step_run(info=info, step_failed=step_failed)

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
        self.validate(fail_if_secrets_missing=True)
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
