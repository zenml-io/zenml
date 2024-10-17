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
"""Base Step for ZenML."""

import copy
import hashlib
import inspect
from abc import abstractmethod
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from pydantic import BaseModel, ConfigDict, ValidationError

from zenml.client_lazy_loader import ClientLazyLoader
from zenml.config.retry_config import StepRetryConfig
from zenml.config.source import Source
from zenml.constants import (
    CODE_HASH_PARAMETER_NAME,
    ENV_ZENML_RUN_SINGLE_STEPS_WITHOUT_STACK,
    handle_bool_env_var,
)
from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.materializer_registry import materializer_registry
from zenml.steps.entrypoint_function_utils import (
    StepArtifact,
    validate_entrypoint_function,
)
from zenml.steps.utils import (
    resolve_type_annotation,
    run_as_single_step_pipeline,
)
from zenml.utils import (
    dict_utils,
    materializer_utils,
    notebook_utils,
    pydantic_utils,
    settings_utils,
    source_code_utils,
    source_utils,
)

if TYPE_CHECKING:
    from zenml.artifacts.external_artifact import ExternalArtifact
    from zenml.artifacts.external_artifact_config import (
        ExternalArtifactConfiguration,
    )
    from zenml.config.base_settings import SettingsOrDict
    from zenml.config.step_configurations import (
        PartialArtifactConfiguration,
        PartialStepConfiguration,
        StepConfiguration,
        StepConfigurationUpdate,
    )
    from zenml.model.lazy_load import ModelVersionDataLazyLoader
    from zenml.model.model import Model
    from zenml.types import HookSpecification

    MaterializerClassOrSource = Union[str, Source, Type["BaseMaterializer"]]
    OutputMaterializersSpecification = Union[
        "MaterializerClassOrSource",
        Sequence["MaterializerClassOrSource"],
        Mapping[str, "MaterializerClassOrSource"],
        Mapping[str, Sequence["MaterializerClassOrSource"]],
    ]

logger = get_logger(__name__)

T = TypeVar("T", bound="BaseStep")


class BaseStep:
    """Abstract base class for all ZenML steps."""

    def __init__(
        self,
        name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        experiment_tracker: Optional[str] = None,
        step_operator: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_materializers: Optional[
            "OutputMaterializersSpecification"
        ] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        model: Optional["Model"] = None,
        retry: Optional[StepRetryConfig] = None,
    ) -> None:
        """Initializes a step.

        Args:
            name: The name of the step.
            enable_cache: If caching should be enabled for this step.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this step.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this step.
            enable_step_logs: Enable step logs for this step.
            experiment_tracker: The experiment tracker to use for this step.
            step_operator: The step operator to use for this step.
            parameters: Function parameters for this step
            output_materializers: Output materializers for this step. If
                given as a dict, the keys must be a subset of the output names
                of this step. If a single value (type or string) is given, the
                materializer will be used for all outputs.
            settings: settings for this step.
            extra: Extra configurations for this step.
            on_failure: Callback function in event of failure of the step. Can
                be a function with a single argument of type `BaseException`, or
                a source path to such a function (e.g. `module.my_function`).
            on_success: Callback function in event of success of the step. Can
                be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`).
            model: configuration of the model version in the Model Control Plane.
            retry: Configuration for retrying the step in case of failure.
        """
        from zenml.config.step_configurations import PartialStepConfiguration

        self.entrypoint_definition = validate_entrypoint_function(
            self.entrypoint, reserved_arguments=["after", "id"]
        )

        name = name or self.__class__.__name__

        logger.debug(
            "Step `%s`: Caching %s.",
            name,
            "enabled" if enable_cache is not False else "disabled",
        )
        logger.debug(
            "Step `%s`: Artifact metadata %s.",
            name,
            "enabled" if enable_artifact_metadata is not False else "disabled",
        )
        logger.debug(
            "Step `%s`: Artifact visualization %s.",
            name,
            "enabled"
            if enable_artifact_visualization is not False
            else "disabled",
        )
        logger.debug(
            "Step `%s`: logs %s.",
            name,
            "enabled" if enable_step_logs is not False else "disabled",
        )
        if model is not None:
            logger.debug(
                "Step `%s`: Is in Model context %s.",
                name,
                {
                    "model": model.name,
                    "version": model.version,
                },
            )

        self._configuration = PartialStepConfiguration(
            name=name,
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            enable_artifact_visualization=enable_artifact_visualization,
            enable_step_logs=enable_step_logs,
        )
        self.configure(
            experiment_tracker=experiment_tracker,
            step_operator=step_operator,
            output_materializers=output_materializers,
            parameters=parameters,
            settings=settings,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
            model=model,
            retry=retry,
        )

        notebook_utils.try_to_save_notebook_cell_code(self.source_object)

    @abstractmethod
    def entrypoint(self, *args: Any, **kwargs: Any) -> Any:
        """Abstract method for core step logic.

        Args:
            *args: Positional arguments passed to the step.
            **kwargs: Keyword arguments passed to the step.

        Returns:
            The output of the step.
        """

    @classmethod
    def load_from_source(cls, source: Union[Source, str]) -> "BaseStep":
        """Loads a step from source.

        Args:
            source: The path to the step source.

        Returns:
            The loaded step.

        Raises:
            ValueError: If the source is not a valid step source.
        """
        obj = source_utils.load(source)

        if isinstance(obj, BaseStep):
            return obj
        elif isinstance(obj, type) and issubclass(obj, BaseStep):
            return obj()
        else:
            raise ValueError("Invalid step source.")

    def resolve(self) -> Source:
        """Resolves the step.

        Returns:
            The step source.
        """
        return source_utils.resolve(self.__class__)

    @property
    def source_object(self) -> Any:
        """The source object of this step.

        Returns:
            The source object of this step.
        """
        return self.__class__

    @property
    def source_code(self) -> str:
        """The source code of this step.

        Returns:
            The source code of this step.
        """
        return inspect.getsource(self.source_object)

    @property
    def docstring(self) -> Optional[str]:
        """The docstring of this step.

        Returns:
            The docstring of this step.
        """
        return self.__doc__

    @property
    def caching_parameters(self) -> Dict[str, Any]:
        """Caching parameters for this step.

        Returns:
            A dictionary containing the caching parameters
        """
        parameters = {
            CODE_HASH_PARAMETER_NAME: source_code_utils.get_hashed_source_code(
                self.source_object
            )
        }
        for name, output in self.configuration.outputs.items():
            if output.materializer_source:
                key = f"{name}_materializer_source"
                hash_ = hashlib.md5()  # nosec

                for source in output.materializer_source:
                    materializer_class = source_utils.load(source)
                    code_hash = source_code_utils.get_hashed_source_code(
                        materializer_class
                    )
                    hash_.update(code_hash.encode())

                parameters[key] = hash_.hexdigest()

        return parameters

    def _parse_call_args(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[
        Dict[str, "StepArtifact"],
        Dict[str, "ExternalArtifact"],
        Dict[str, "ModelVersionDataLazyLoader"],
        Dict[str, "ClientLazyLoader"],
        Dict[str, Any],
        Dict[str, Any],
    ]:
        """Parses the call args for the step entrypoint.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Raises:
            StepInterfaceError: If invalid function arguments were passed.

        Returns:
            The artifacts, external artifacts, model version artifacts/metadata and parameters for the step.
        """
        from zenml.artifacts.external_artifact import ExternalArtifact
        from zenml.model.lazy_load import ModelVersionDataLazyLoader
        from zenml.models.v2.core.artifact_version import (
            LazyArtifactVersionResponse,
        )

        signature = inspect.signature(self.entrypoint, follow_wrapped=True)

        try:
            bound_args = signature.bind_partial(*args, **kwargs)
        except TypeError as e:
            raise StepInterfaceError(
                f"Wrong arguments when calling step '{self.name}': {e}"
            ) from e

        artifacts = {}
        external_artifacts = {}
        model_artifacts_or_metadata = {}
        client_lazy_loaders = {}
        parameters = {}
        default_parameters = {}

        for key, value in bound_args.arguments.items():
            self.entrypoint_definition.validate_input(key=key, value=value)

            if isinstance(value, StepArtifact):
                artifacts[key] = value
                if key in self.configuration.parameters:
                    logger.warning(
                        "Got duplicate value for step input %s, using value "
                        "provided as artifact.",
                        key,
                    )
            elif isinstance(value, ExternalArtifact):
                external_artifacts[key] = value
                if not value.id:
                    # If the external artifact references a fixed artifact by
                    # ID, caching behaves as expected.
                    logger.warning(
                        "Using an external artifact as step input currently "
                        "invalidates caching for the step and all downstream "
                        "steps. Future releases will introduce hashing of "
                        "artifacts which will improve this behavior."
                    )
            elif isinstance(value, LazyArtifactVersionResponse):
                model_artifacts_or_metadata[key] = ModelVersionDataLazyLoader(
                    model_name=value.lazy_load_model_name,
                    model_version=value.lazy_load_model_version,
                    artifact_name=value.lazy_load_name,
                    artifact_version=value.lazy_load_version,
                    metadata_name=None,
                )
            elif isinstance(value, ClientLazyLoader):
                client_lazy_loaders[key] = value
            else:
                parameters[key] = value

        # Above we iterated over the provided arguments which should overwrite
        # any parameters previously defined on the step instance. Now we apply
        # the default values on the entrypoint function and add those as
        # parameters for any argument that has no value yet. If we were to do
        # that in the above loop, we would overwrite previously configured
        # parameters with the default values.
        bound_args.apply_defaults()
        for key, value in bound_args.arguments.items():
            self.entrypoint_definition.validate_input(key=key, value=value)
            if (
                key not in artifacts
                and key not in external_artifacts
                and key not in model_artifacts_or_metadata
                and key not in self.configuration.parameters
                and key not in client_lazy_loaders
            ):
                default_parameters[key] = value

        return (
            artifacts,
            external_artifacts,
            model_artifacts_or_metadata,
            client_lazy_loaders,
            parameters,
            default_parameters,
        )

    def __call__(
        self,
        *args: Any,
        id: Optional[str] = None,
        after: Union[str, Sequence[str], None] = None,
        **kwargs: Any,
    ) -> Any:
        """Handle a call of the step.

        This method does one of two things:
        * If there is an active pipeline context, it adds an invocation of the
          step instance to the pipeline.
        * If no pipeline is active, it calls the step entrypoint function.

        Args:
            *args: Entrypoint function arguments.
            id: Invocation ID to use.
            after: Upstream steps for the invocation.
            **kwargs: Entrypoint function keyword arguments.

        Returns:
            The outputs of the entrypoint function call.
        """
        from zenml.pipelines.pipeline_definition import Pipeline

        if not Pipeline.ACTIVE_PIPELINE:
            from zenml import constants, get_step_context

            # If the environment variable was set to explicitly not run on the
            # stack, we do that.
            run_without_stack = handle_bool_env_var(
                ENV_ZENML_RUN_SINGLE_STEPS_WITHOUT_STACK, default=False
            )
            if run_without_stack:
                return self.call_entrypoint(*args, **kwargs)

            try:
                get_step_context()
            except RuntimeError:
                pass
            else:
                # We're currently inside the execution of a different step
                # -> We don't want to launch another single step pipeline here,
                # but instead just call the step function
                return self.call_entrypoint(*args, **kwargs)

            if constants.SHOULD_PREVENT_PIPELINE_EXECUTION:
                logger.info(
                    "Preventing execution of step '%s'.",
                    self.name,
                )
                return

            return run_as_single_step_pipeline(self, *args, **kwargs)

        (
            input_artifacts,
            external_artifacts,
            model_artifacts_or_metadata,
            client_lazy_loaders,
            parameters,
            default_parameters,
        ) = self._parse_call_args(*args, **kwargs)

        upstream_steps = {
            artifact.invocation_id for artifact in input_artifacts.values()
        }
        if isinstance(after, str):
            upstream_steps.add(after)
        elif isinstance(after, Sequence):
            upstream_steps = upstream_steps.union(after)

        invocation_id = Pipeline.ACTIVE_PIPELINE.add_step_invocation(
            step=self,
            input_artifacts=input_artifacts,
            external_artifacts=external_artifacts,
            model_artifacts_or_metadata=model_artifacts_or_metadata,
            client_lazy_loaders=client_lazy_loaders,
            parameters=parameters,
            default_parameters=default_parameters,
            upstream_steps=upstream_steps,
            custom_id=id,
            allow_id_suffix=not id,
        )

        outputs = []
        for key, annotation in self.entrypoint_definition.outputs.items():
            output = StepArtifact(
                invocation_id=invocation_id,
                output_name=key,
                annotation=annotation,
                pipeline=Pipeline.ACTIVE_PIPELINE,
            )
            outputs.append(output)
        return outputs[0] if len(outputs) == 1 else outputs

    def call_entrypoint(self, *args: Any, **kwargs: Any) -> Any:
        """Calls the entrypoint function of the step.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Returns:
            The return value of the entrypoint function.

        Raises:
            StepInterfaceError: If the arguments to the entrypoint function are
                invalid.
        """
        try:
            validated_args = pydantic_utils.validate_function_args(
                self.entrypoint,
                ConfigDict(arbitrary_types_allowed=True),
                *args,
                **kwargs,
            )
        except ValidationError as e:
            raise StepInterfaceError(
                "Invalid step function entrypoint arguments. Check out the "
                "pydantic error above for more details."
            ) from e

        return self.entrypoint(**validated_args)

    @property
    def name(self) -> str:
        """The name of the step.

        Returns:
            The name of the step.
        """
        return self.configuration.name

    @property
    def enable_cache(self) -> Optional[bool]:
        """If caching is enabled for the step.

        Returns:
            If caching is enabled for the step.
        """
        return self.configuration.enable_cache

    @property
    def configuration(self) -> "PartialStepConfiguration":
        """The configuration of the step.

        Returns:
            The configuration of the step.
        """
        return self._configuration

    def configure(
        self: T,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        experiment_tracker: Optional[str] = None,
        step_operator: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_materializers: Optional[
            "OutputMaterializersSpecification"
        ] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        model: Optional["Model"] = None,
        merge: bool = True,
        retry: Optional[StepRetryConfig] = None,
    ) -> T:
        """Configures the step.

        Configuration merging example:
        * `merge==True`:
            step.configure(extra={"key1": 1})
            step.configure(extra={"key2": 2}, merge=True)
            step.configuration.extra # {"key1": 1, "key2": 2}
        * `merge==False`:
            step.configure(extra={"key1": 1})
            step.configure(extra={"key2": 2}, merge=False)
            step.configuration.extra # {"key2": 2}

        Args:
            enable_cache: If caching should be enabled for this step.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this step.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this step.
            enable_step_logs: If step logs should be enabled for this step.
            experiment_tracker: The experiment tracker to use for this step.
            step_operator: The step operator to use for this step.
            parameters: Function parameters for this step
            output_materializers: Output materializers for this step. If
                given as a dict, the keys must be a subset of the output names
                of this step. If a single value (type or string) is given, the
                materializer will be used for all outputs.
            settings: settings for this step.
            extra: Extra configurations for this step.
            on_failure: Callback function in event of failure of the step. Can
                be a function with a single argument of type `BaseException`, or
                a source path to such a function (e.g. `module.my_function`).
            on_success: Callback function in event of success of the step. Can
                be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`).
            model: configuration of the model version in the Model Control Plane.
            merge: If `True`, will merge the given dictionary configurations
                like `parameters` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.
            retry: Configuration for retrying the step in case of failure.

        Returns:
            The step instance that this method was called on.
        """
        from zenml.config.step_configurations import StepConfigurationUpdate
        from zenml.hooks.hook_validators import resolve_and_validate_hook

        def _resolve_if_necessary(
            value: Union[str, Source, Type[Any]],
        ) -> Source:
            if isinstance(value, str):
                return Source.from_import_path(value)
            elif isinstance(value, Source):
                return value
            else:
                return source_utils.resolve(value)

        def _convert_to_tuple(value: Any) -> Tuple[Source, ...]:
            if isinstance(value, str) or not isinstance(value, Sequence):
                return (_resolve_if_necessary(value),)
            else:
                return tuple(_resolve_if_necessary(v) for v in value)

        outputs: Dict[str, Dict[str, Tuple[Source, ...]]] = defaultdict(dict)
        allowed_output_names = set(self.entrypoint_definition.outputs)

        if output_materializers:
            if not isinstance(output_materializers, Mapping):
                sources = _convert_to_tuple(output_materializers)
                output_materializers = {
                    output_name: sources
                    for output_name in allowed_output_names
                }

            for output_name, materializer in output_materializers.items():
                sources = _convert_to_tuple(materializer)
                outputs[output_name]["materializer_source"] = sources

        failure_hook_source = None
        if on_failure:
            # string of on_failure hook function to be used for this step
            failure_hook_source = resolve_and_validate_hook(on_failure)

        success_hook_source = None
        if on_success:
            # string of on_success hook function to be used for this step
            success_hook_source = resolve_and_validate_hook(on_success)

        values = dict_utils.remove_none_values(
            {
                "enable_cache": enable_cache,
                "enable_artifact_metadata": enable_artifact_metadata,
                "enable_artifact_visualization": enable_artifact_visualization,
                "enable_step_logs": enable_step_logs,
                "experiment_tracker": experiment_tracker,
                "step_operator": step_operator,
                "parameters": parameters,
                "settings": settings,
                "outputs": outputs or None,
                "extra": extra,
                "failure_hook_source": failure_hook_source,
                "success_hook_source": success_hook_source,
                "model": model,
                "retry": retry,
            }
        )
        config = StepConfigurationUpdate(**values)
        self._apply_configuration(config, merge=merge)
        return self

    def with_options(
        self,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        enable_artifact_visualization: Optional[bool] = None,
        enable_step_logs: Optional[bool] = None,
        experiment_tracker: Optional[str] = None,
        step_operator: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_materializers: Optional[
            "OutputMaterializersSpecification"
        ] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        model: Optional["Model"] = None,
        merge: bool = True,
    ) -> "BaseStep":
        """Copies the step and applies the given configurations.

        Args:
            enable_cache: If caching should be enabled for this step.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this step.
            enable_artifact_visualization: If artifact visualization should be
                enabled for this step.
            enable_step_logs: If step logs should be enabled for this step.
            experiment_tracker: The experiment tracker to use for this step.
            step_operator: The step operator to use for this step.
            parameters: Function parameters for this step
            output_materializers: Output materializers for this step. If
                given as a dict, the keys must be a subset of the output names
                of this step. If a single value (type or string) is given, the
                materializer will be used for all outputs.
            settings: settings for this step.
            extra: Extra configurations for this step.
            on_failure: Callback function in event of failure of the step. Can
                be a function with a single argument of type `BaseException`, or
                a source path to such a function (e.g. `module.my_function`).
            on_success: Callback function in event of success of the step. Can
                be a function with no arguments, or a source path to such a
                function (e.g. `module.my_function`).
            model: configuration of the model version in the Model Control Plane.
            merge: If `True`, will merge the given dictionary configurations
                like `parameters` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.

        Returns:
            The copied step instance.
        """
        step_copy = self.copy()
        step_copy.configure(
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
            enable_artifact_visualization=enable_artifact_visualization,
            enable_step_logs=enable_step_logs,
            experiment_tracker=experiment_tracker,
            step_operator=step_operator,
            parameters=parameters,
            output_materializers=output_materializers,
            settings=settings,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
            model=model,
            merge=merge,
        )
        return step_copy

    def copy(self) -> "BaseStep":
        """Copies the step.

        Returns:
            The step copy.
        """
        return copy.deepcopy(self)

    def _apply_configuration(
        self,
        config: "StepConfigurationUpdate",
        merge: bool = True,
        runtime_parameters: Dict[str, Any] = {},
    ) -> None:
        """Applies an update to the step configuration.

        Args:
            config: The configuration update.
            runtime_parameters: Dictionary of parameters passed to a step from runtime
            merge: Whether to merge the updates with the existing configuration
                or not. See the `BaseStep.configure(...)` method for a detailed
                explanation.
        """
        self._validate_configuration(config, runtime_parameters)

        self._configuration = pydantic_utils.update_model(
            self._configuration, update=config, recursive=merge
        )

        logger.debug("Updated step configuration:")
        logger.debug(self._configuration)

    def _validate_configuration(
        self,
        config: "StepConfigurationUpdate",
        runtime_parameters: Dict[str, Any],
    ) -> None:
        """Validates a configuration update.

        Args:
            config: The configuration update to validate.
            runtime_parameters: Dictionary of parameters passed to a step from runtime
        """
        settings_utils.validate_setting_keys(list(config.settings))
        self._validate_function_parameters(
            parameters=config.parameters, runtime_parameters=runtime_parameters
        )
        self._validate_outputs(outputs=config.outputs)

    def _validate_function_parameters(
        self,
        parameters: Dict[str, Any],
        runtime_parameters: Dict[str, Any],
    ) -> None:
        """Validates step function parameters.

        Args:
            parameters: The parameters to validate.
            runtime_parameters: Dictionary of parameters passed to a step from runtime

        Raises:
            StepInterfaceError: If the step requires no function parameters but
                parameters were configured.
            RuntimeError: If the step has parameters configured differently in
                configuration file and code.
        """
        if not parameters:
            return

        conflicting_parameters = {}
        for key, value in parameters.items():
            if key in runtime_parameters:
                runtime_value = runtime_parameters[key]
                if runtime_value != value:
                    conflicting_parameters[key] = (value, runtime_value)
            if key in self.entrypoint_definition.inputs:
                self.entrypoint_definition.validate_input(key=key, value=value)
            else:
                raise StepInterfaceError(
                    f"Unable to find parameter '{key}' in step function "
                    "signature."
                )
        if conflicting_parameters:
            is_plural = "s" if len(conflicting_parameters) > 1 else ""
            msg = f"Configured parameter{is_plural} for the step '{self.name}' conflict{'' if not is_plural else 's'} with parameter{is_plural} passed in runtime:\n"
            for key, values in conflicting_parameters.items():
                msg += (
                    f"`{key}`: config=`{values[0]}` | runtime=`{values[1]}`\n"
                )
            msg += """This happens, if you define values for step parameters in configuration file and pass same parameters from the code. Example:
```
# config.yaml

steps:
    step_name:
        parameters:
            param_name: value1
            
            
# pipeline.py

@pipeline
def pipeline_():
    step_name(param_name="other_value")
```
To avoid this consider setting step parameters only in one place (config or code).
"""
            raise RuntimeError(msg)

    def _validate_outputs(
        self, outputs: Mapping[str, "PartialArtifactConfiguration"]
    ) -> None:
        """Validates the step output configuration.

        Args:
            outputs: The configured step outputs.

        Raises:
            StepInterfaceError: If an output for a non-existent name is
                configured of an output artifact/materializer source does not
                resolve to the correct class.
        """
        allowed_output_names = set(self.entrypoint_definition.outputs)
        for output_name, output in outputs.items():
            if output_name not in allowed_output_names:
                raise StepInterfaceError(
                    f"Got unexpected materializers for non-existent "
                    f"output '{output_name}' in step '{self.name}'. "
                    f"Only materializers for the outputs "
                    f"{allowed_output_names} of this step can"
                    f" be registered."
                )

            if output.materializer_source:
                for source in output.materializer_source:
                    if not source_utils.validate_source_class(
                        source, expected_class=BaseMaterializer
                    ):
                        raise StepInterfaceError(
                            f"Materializer source `{source}` "
                            f"for output '{output_name}' of step '{self.name}' "
                            "does not resolve to a `BaseMaterializer` subclass."
                        )

    def _validate_inputs(
        self,
        input_artifacts: Dict[str, "StepArtifact"],
        external_artifacts: Dict[str, "ExternalArtifactConfiguration"],
        model_artifacts_or_metadata: Dict[str, "ModelVersionDataLazyLoader"],
        client_lazy_loaders: Dict[str, "ClientLazyLoader"],
    ) -> None:
        """Validates the step inputs.

        This method makes sure that all inputs are provided either as an
        artifact or parameter.

        Args:
            input_artifacts: The input artifacts.
            external_artifacts: The external input artifacts.
            model_artifacts_or_metadata: The model artifacts or metadata.
            client_lazy_loaders: The client lazy loaders.

        Raises:
            StepInterfaceError: If an entrypoint input is missing.
        """
        for key in self.entrypoint_definition.inputs.keys():
            if (
                key in input_artifacts
                or key in self.configuration.parameters
                or key in external_artifacts
                or key in model_artifacts_or_metadata
                or key in client_lazy_loaders
            ):
                continue
            raise StepInterfaceError(
                f"Missing entrypoint input '{key}' in step '{self.name}'."
            )

    def _finalize_configuration(
        self,
        input_artifacts: Dict[str, "StepArtifact"],
        external_artifacts: Dict[str, "ExternalArtifactConfiguration"],
        model_artifacts_or_metadata: Dict[str, "ModelVersionDataLazyLoader"],
        client_lazy_loaders: Dict[str, "ClientLazyLoader"],
    ) -> "StepConfiguration":
        """Finalizes the configuration after the step was called.

        Once the step was called, we know the outputs of previous steps
        and that no additional user configurations will be made. That means
        we can now collect the remaining artifact and materializer types
        as well as check for the completeness of the step function parameters.

        Args:
            input_artifacts: The input artifacts of this step.
            external_artifacts: The external artifacts of this step.
            model_artifacts_or_metadata: The model artifacts or metadata of
                this step.
            client_lazy_loaders: The client lazy loaders of this step.

        Raises:
            StepInterfaceError: If explicit materializers were specified for an
                output but they do not work for the data type(s) defined by
                the type annotation.

        Returns:
            The finalized step configuration.
        """
        from zenml.config.step_configurations import (
            PartialArtifactConfiguration,
            StepConfiguration,
            StepConfigurationUpdate,
        )

        outputs: Dict[str, Dict[str, Any]] = defaultdict(dict)

        for (
            output_name,
            output_annotation,
        ) in self.entrypoint_definition.outputs.items():
            output = self._configuration.outputs.get(
                output_name, PartialArtifactConfiguration()
            )
            if artifact_config := output_annotation.artifact_config:
                outputs[output_name]["artifact_config"] = artifact_config

            if output.materializer_source:
                # The materializer source was configured by the user. We
                # validate that their configured materializer supports the
                # output type. If the output annotation is a Union, we check
                # that at least one of the specified materializers works with at
                # least one of the types in the Union. If that's not the case,
                # it would be a guaranteed failure at runtime and we fail early
                # here.
                if output_annotation.resolved_annotation is Any:
                    continue

                materializer_classes: List[Type["BaseMaterializer"]] = [
                    source_utils.load(materializer_source)
                    for materializer_source in output.materializer_source
                ]

                for data_type in output_annotation.get_output_types():
                    try:
                        materializer_utils.select_materializer(
                            data_type=data_type,
                            materializer_classes=materializer_classes,
                        )
                        break
                    except RuntimeError:
                        pass
                else:
                    materializer_strings = [
                        materializer_source.import_path
                        for materializer_source in output.materializer_source
                    ]
                    raise StepInterfaceError(
                        "Invalid materializers specified for output "
                        f"{output_name} of step {self.name}. None of the "
                        f"materializers ({materializer_strings}) are "
                        "able to save or load data of the type that is defined "
                        "for the output "
                        f"({output_annotation.resolved_annotation})."
                    )
            else:
                if output_annotation.resolved_annotation is Any:
                    outputs[output_name]["materializer_source"] = ()
                    outputs[output_name]["default_materializer_source"] = (
                        source_utils.resolve(
                            materializer_registry.get_default_materializer()
                        )
                    )
                    continue

                materializer_sources = []

                for output_type in output_annotation.get_output_types():
                    materializer_class = materializer_registry[output_type]
                    materializer_sources.append(
                        source_utils.resolve(materializer_class)
                    )

                outputs[output_name]["materializer_source"] = tuple(
                    materializer_sources
                )

        parameters = self._finalize_parameters()
        self.configure(parameters=parameters, merge=False)
        self._validate_inputs(
            input_artifacts=input_artifacts,
            external_artifacts=external_artifacts,
            model_artifacts_or_metadata=model_artifacts_or_metadata,
            client_lazy_loaders=client_lazy_loaders,
        )

        values = dict_utils.remove_none_values({"outputs": outputs or None})
        config = StepConfigurationUpdate(**values)
        self._apply_configuration(config)

        self._configuration = self._configuration.model_copy(
            update={
                "caching_parameters": self.caching_parameters,
                "external_input_artifacts": external_artifacts,
                "model_artifacts_or_metadata": model_artifacts_or_metadata,
                "client_lazy_loaders": client_lazy_loaders,
            }
        )

        return StepConfiguration.model_validate(
            self._configuration.model_dump()
        )

    def _finalize_parameters(self) -> Dict[str, Any]:
        """Finalizes the config parameters for running this step.

        Returns:
            All parameter values for running this step.
        """
        params = {}
        for key, value in self.configuration.parameters.items():
            if key not in self.entrypoint_definition.inputs:
                continue

            annotation = self.entrypoint_definition.inputs[key].annotation
            annotation = resolve_type_annotation(annotation)
            if inspect.isclass(annotation) and issubclass(
                annotation, BaseModel
            ):
                # Make sure we have all necessary values to instantiate the
                # pydantic model later
                model = annotation(**value)
                params[key] = model.model_dump()
            else:
                params[key] = value

        return params
