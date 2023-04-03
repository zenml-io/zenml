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

import inspect
from abc import abstractmethod
from collections import defaultdict
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

from pydantic import BaseModel, Extra, ValidationError

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.config.source import Source
from zenml.config.step_configurations import (
    PartialArtifactConfiguration,
    PartialStepConfiguration,
    StepConfiguration,
    StepConfigurationUpdate,
)
from zenml.constants import STEP_SOURCE_PARAMETER_NAME
from zenml.exceptions import MissingStepParameterError, StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.default_materializer_registry import (
    default_materializer_registry,
)
from zenml.steps.base_parameters import BaseParameters
from zenml.steps.step_context import StepContext
from zenml.steps.utils import (
    parse_return_type_annotations,
    resolve_type_annotation,
)
from zenml.utils import (
    dict_utils,
    pydantic_utils,
    settings_utils,
    source_code_utils,
    source_utils,
)

if TYPE_CHECKING:
    from zenml.config.base_settings import SettingsOrDict
    from zenml.pipelines.new import Pipeline

    ParametersOrDict = Union["BaseParameters", Dict[str, Any]]
    ArtifactClassOrStr = Union[str, Type["BaseArtifact"]]
    MaterializerClassOrSource = Union[str, Source, Type["BaseMaterializer"]]
    HookSpecification = Union[str, Source, FunctionType]
    OutputArtifactsSpecification = Union[
        "ArtifactClassOrStr", Mapping[str, "ArtifactClassOrStr"]
    ]
    OutputMaterializersSpecification = Union[
        "MaterializerClassOrSource", Mapping[str, "MaterializerClassOrSource"]
    ]

logger = get_logger(__name__)


class BaseStepMeta(type):
    """Metaclass for `BaseStep`.

    Makes sure that the entrypoint function has valid parameters and type
    annotations.
    """

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseStepMeta":
        """Set up a new class with a qualified spec.

        Args:
            name: The name of the class.
            bases: The base classes of the class.
            dct: The attributes of the class.

        Returns:
            The new class.

        Raises:
            StepInterfaceError: When unable to create the step.
        """
        from zenml.steps.base_parameters import BaseParameters

        cls = cast(Type["BaseStep"], super().__new__(mcs, name, bases, dct))

        cls.INPUT_SIGNATURE = {}
        cls.OUTPUT_SIGNATURE = {}
        cls.PARAMETERS_FUNCTION_PARAMETER_NAME = None
        cls.PARAMETERS_CLASS = None
        cls.CONTEXT_PARAMETER_NAME = None

        # Get the signature of the step function
        step_function_signature = inspect.getfullargspec(
            inspect.unwrap(cls.entrypoint)
        )

        if name not in {"BaseStep", "_DecoratedStep"}:
            # We're not creating one of the abstract base classes
            # but a concrete implementation. Make sure the step function
            # signature does not contain variable *args or **kwargs
            variable_arguments = None
            if step_function_signature.varargs:
                variable_arguments = f"*{step_function_signature.varargs}"
            elif step_function_signature.varkw:
                variable_arguments = f"**{step_function_signature.varkw}"

            if variable_arguments:
                raise StepInterfaceError(
                    f"Unable to create step '{name}' with variable arguments "
                    f"'{variable_arguments}'. Please make sure your step "
                    f"functions are defined with a fixed amount of arguments."
                )

        step_function_args = (
            step_function_signature.args + step_function_signature.kwonlyargs
        )

        # Remove 'self' from the signature if it exists
        if step_function_args and step_function_args[0] == "self":
            step_function_args.pop(0)

        # Verify the input arguments of the step function
        for arg in step_function_args:
            arg_type = step_function_signature.annotations.get(arg, None)
            arg_type = resolve_type_annotation(arg_type)

            if not arg_type:
                raise StepInterfaceError(
                    f"Missing type annotation for argument '{arg}' when "
                    f"trying to create step '{name}'. Please make sure to "
                    f"include type annotations for all your step inputs "
                    f"and outputs."
                )

            if inspect.isclass(arg_type) and issubclass(
                arg_type, BaseParameters
            ):
                # Raise an error if we already found a config in the signature
                if cls.PARAMETERS_CLASS is not None:
                    raise StepInterfaceError(
                        f"Found multiple parameter arguments "
                        f"('{cls.PARAMETERS_FUNCTION_PARAMETER_NAME}' and '{arg}') when "
                        f"trying to create step '{name}'. Please make sure to "
                        f"only have one `Parameters` subclass as input "
                        f"argument for a step."
                    )
                cls.PARAMETERS_FUNCTION_PARAMETER_NAME = arg
                cls.PARAMETERS_CLASS = arg_type

            elif inspect.isclass(arg_type) and issubclass(
                arg_type, StepContext
            ):
                if cls.CONTEXT_PARAMETER_NAME is not None:
                    raise StepInterfaceError(
                        f"Found multiple context arguments "
                        f"('{cls.CONTEXT_PARAMETER_NAME}' and '{arg}') when "
                        f"trying to create step '{name}'. Please make sure to "
                        f"only have one `StepContext` as input "
                        f"argument for a step."
                    )
                cls.CONTEXT_PARAMETER_NAME = arg
            else:
                # Can't do any check for existing materializers right now
                # as they might get be defined later, so we simply store the
                # argument name and type for later use.
                cls.INPUT_SIGNATURE.update({arg: arg_type})

        # Parse the returns of the step function
        if "return" not in step_function_signature.annotations:
            raise StepInterfaceError(
                "Missing return type annotation when trying to create step "
                f"'{name}'. Please make sure to include type annotations for "
                "all your step inputs and outputs. If your step returns "
                "nothing, please annotate it with `-> None`."
            )
        cls.OUTPUT_SIGNATURE = parse_return_type_annotations(
            step_function_signature.annotations,
        )

        return cls

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        from zenml.pipelines.new import Pipeline

        if not Pipeline.ACTIVE_PIPELINE:
            return super().__call__(*args, **kwargs)

        init_kwargs = {}
        call_kwargs = {}

        # TODO: validate the entrypoint does not define reserved params like
        # "settings" or "extra"
        entrypoint_params = set(inspect.signature(self.entrypoint).parameters)
        entrypoint_params.add("after")
        entrypoint_params.add("id")

        for key, value in kwargs.items():
            if key in entrypoint_params:
                call_kwargs[key] = value
            else:
                init_kwargs[key] = value

        step_instance = super().__call__(**init_kwargs)
        return step_instance(*args, **call_kwargs)


T = TypeVar("T", bound="BaseStep")


class BaseStep(metaclass=BaseStepMeta):
    """Abstract base class for all ZenML steps.

    Attributes:
        name: The name of this step.
        pipeline_parameter_name: The name of the pipeline parameter for which
            this step was passed as an argument.
        enable_cache: A boolean indicating if caching is enabled for this step.
        enable_artifact_metadata: A boolean indicating if artifact metadata
            is enabled for this step.
    """

    INPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    OUTPUT_SIGNATURE: ClassVar[Dict[str, Type[Any]]] = None  # type: ignore[assignment] # noqa
    PARAMETERS_FUNCTION_PARAMETER_NAME: ClassVar[Optional[str]] = None
    PARAMETERS_CLASS: ClassVar[Optional[Type["BaseParameters"]]] = None
    CONTEXT_PARAMETER_NAME: ClassVar[Optional[str]] = None

    class _OutputArtifact(NamedTuple):
        """Internal step output artifact.

        This class is used for inputs/outputs of the __call__ method of
        BaseStep. It passes all the information about step outputs so downstream
        steps can finalize their configuration.

        Attributes:
            name: Name of the output.
            step_name: Name of the step that produced this output.
        """

        name: str
        step_name: str
        pipeline: "Pipeline"

    def __init__(
        self,
        *args: Any,
        name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        experiment_tracker: Optional[str] = None,
        step_operator: Optional[str] = None,
        parameters: Optional["ParametersOrDict"] = None,
        output_materializers: Optional[
            "OutputMaterializersSpecification"
        ] = None,
        output_artifacts: Optional["OutputArtifactsSpecification"] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        **kwargs: Any,
    ) -> None:
        """Initializes a step.

        Args:
            *args: Positional arguments passed to the step.
            **kwargs: Keyword arguments passed to the step.
        """
        self._upstream_steps: Set[str] = set()
        name = name or self.__class__.__name__

        requires_context = bool(self.CONTEXT_PARAMETER_NAME)
        if enable_cache is None:
            if requires_context:
                # Using the StepContext inside a step provides access to
                # external resources which might influence the step execution.
                # We therefore disable caching unless it is explicitly enabled
                enable_cache = False
                logger.debug(
                    "Step '%s': Step context required and caching not "
                    "explicitly enabled.",
                    name,
                )

        logger.debug(
            "Step '%s': Caching %s.",
            name,
            "enabled" if enable_cache is not False else "disabled",
        )
        logger.debug(
            "Step '%s': Artifact metadata %s.",
            name,
            "enabled" if enable_artifact_metadata is not False else "disabled",
        )

        self._configuration = PartialStepConfiguration(
            name=name,
            enable_cache=enable_cache,
            enable_artifact_metadata=enable_artifact_metadata,
        )
        self.configure(
            experiment_tracker=experiment_tracker,
            step_operator=step_operator,
            output_artifacts=output_artifacts,
            output_materializers=output_materializers,
            parameters=parameters,
            settings=settings,
            extra=extra,
            on_failure=on_failure,
            on_success=on_success,
        )
        self._verify_and_apply_init_params(*args, **kwargs)

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
        """
        step_class: Type[BaseStep] = source_utils.load_and_validate_class(
            source, expected_class=BaseStep
        )
        return step_class()

    @property
    def upstream_steps(self) -> Set[str]:
        """Names of the upstream steps of this step.

        This property will only contain the full set of upstream steps once
        it's parent pipeline `connect(...)` method was called.

        Returns:
            Set of upstream step names.
        """
        return self._upstream_steps

    def after(self, step: "BaseStep") -> None:
        """Adds an upstream step to this step.

        Calling this method makes sure this step only starts running once the
        given step has successfully finished executing.

        **Note**: This can only be called inside the pipeline connect function
        which is decorated with the `@pipeline` decorator. Any calls outside
        this function will be ignored.

        Example:
        The following pipeline will run its steps sequentially in the following
        order: step_2 -> step_1 -> step_3

        ```python
        @pipeline
        def example_pipeline(step_1, step_2, step_3):
            step_1.after(step_2)
            step_3(step_1(), step_2())
        ```

        Args:
            step: A step which should finish executing before this step is
                started.
        """
        self._upstream_steps.add(step.name)

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
        parameters = {}
        parameters[
            STEP_SOURCE_PARAMETER_NAME
        ] = source_code_utils.get_hashed_source_code(self.source_object)

        for name, output in self.configuration.outputs.items():
            if output.materializer_source:
                key = f"{name}_materializer_source"
                materializer_class = source_utils.load(
                    output.materializer_source
                )
                parameters[key] = source_code_utils.get_hashed_source_code(
                    materializer_class
                )

        return parameters

    def _verify_and_apply_init_params(self, *args: Any, **kwargs: Any) -> None:
        """Verifies the initialization args and kwargs of this step.

        This method makes sure that there is only one parameters object passed
        at initialization and that it was passed using the correct name and
        type specified in the step declaration.

        Args:
            *args: The args passed to the init method of this step.
            **kwargs: The kwargs passed to the init method of this step.

        Raises:
            StepInterfaceError: If there are too many arguments or arguments
                with a wrong name/type.
        """
        maximum_arg_count = 1 if self.PARAMETERS_CLASS else 0
        arg_count = len(args) + len(kwargs)
        if arg_count > maximum_arg_count:
            raise StepInterfaceError(
                f"Too many arguments ({arg_count}, expected: "
                f"{maximum_arg_count}) passed when creating a "
                f"'{self.name}' step."
            )

        if self.PARAMETERS_FUNCTION_PARAMETER_NAME and self.PARAMETERS_CLASS:
            if args:
                config = args[0]
            elif kwargs:
                key, config = kwargs.popitem()

                if key != self.PARAMETERS_FUNCTION_PARAMETER_NAME:
                    raise StepInterfaceError(
                        f"Unknown keyword argument '{key}' when creating a "
                        f"'{self.name}' step, only expected a single "
                        "argument with key "
                        f"'{self.PARAMETERS_FUNCTION_PARAMETER_NAME}'."
                    )
            else:
                # This step requires configuration parameters but no parameters
                # object was passed as an argument. The parameters might be
                # set via default values in the parameters class or in a
                # configuration file, so we continue for now and verify
                # that all parameters are set before running the step
                return

            if not isinstance(config, self.PARAMETERS_CLASS):
                raise StepInterfaceError(
                    f"`{config}` object passed when creating a "
                    f"'{self.name}' step is not a "
                    f"`{self.PARAMETERS_CLASS.__name__}` instance."
                )

            self.configure(parameters=config)

    def _parse_call_args(
        self, *args: Any, **kwargs: Any
    ) -> Tuple[Dict[str, _OutputArtifact], Dict[str, Any]]:
        signature = get_step_entrypoint_signature(step=self)

        try:
            bound_args = signature.bind_partial(*args, **kwargs)
        except TypeError as e:
            raise StepInterfaceError(
                f"Wrong arguments when calling step '{self.name}': {e}"
            ) from e

        bound_args.apply_defaults()

        artifacts = {}
        external_artifacts = {}
        parameters = {}

        for key, value in bound_args.arguments.items():
            if isinstance(value, BaseStep._OutputArtifact):
                artifacts[key] = value
                if key in self.configuration.parameters:
                    logger.warning(
                        "Got duplicate value for step input %s, using value "
                        "provided as artifact.",
                        key,
                    )
            elif isinstance(value, ExternalArtifact):
                external_artifacts[key] = value
                if not value._id:
                    # If the external artifact references a fixed artifact by
                    # ID, caching behaves as expected.
                    logger.warning(
                        "Using an external artifact as step input currently "
                        "invalidates caching for the step and all downstream "
                        "steps. Future releases will introduce hashing of "
                        "artifacts which will improve this behavior."
                    )
            else:
                self._validate_parameter_value(
                    parameter=signature.parameters[key], value=value
                )
                parameters[key] = value

        return artifacts, external_artifacts, parameters

    def __call__(
        self,
        *args: Any,
        id: Optional[str] = None,
        after: Union[str, Sequence[str], None] = None,
        **kwargs: Any,
    ) -> Any:
        from zenml.pipelines.new.pipeline import Pipeline

        if not Pipeline.ACTIVE_PIPELINE:
            # The step is being called outside of the context of a pipeline,
            # we simply call the entrypoint
            return self.entrypoint(*args, **kwargs)

        (
            input_artifacts,
            external_artifacts,
            parameters,
        ) = self._parse_call_args(*args, **kwargs)
        upstream_steps = {
            artifact.step_name for artifact in input_artifacts.values()
        }
        if isinstance(after, str):
            upstream_steps.add(after)
        elif isinstance(after, Sequence):
            upstream_steps.union(after)

        invocation_id = Pipeline.ACTIVE_PIPELINE.add_step(
            step=self,
            input_artifacts=input_artifacts,
            external_artifacts=external_artifacts,
            parameters=parameters,
            upstream_steps=upstream_steps,
            custom_id=id,
            allow_suffix=not id,
        )

        outputs = []
        for key in self.OUTPUT_SIGNATURE:
            output = BaseStep._OutputArtifact(
                name=key,
                step_name=invocation_id,
                pipeline=Pipeline.ACTIVE_PIPELINE,
            )
            outputs.append(output)

        if len(outputs) == 1:
            return outputs[0]
        else:
            return outputs

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
    def configuration(self) -> PartialStepConfiguration:
        """The configuration of the step.

        Returns:
            The configuration of the step.
        """
        return self._configuration

    def configure(
        self: T,
        name: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        enable_artifact_metadata: Optional[bool] = None,
        experiment_tracker: Optional[str] = None,
        step_operator: Optional[str] = None,
        parameters: Optional["ParametersOrDict"] = None,
        output_materializers: Optional[
            "OutputMaterializersSpecification"
        ] = None,
        output_artifacts: Optional["OutputArtifactsSpecification"] = None,
        settings: Optional[Mapping[str, "SettingsOrDict"]] = None,
        extra: Optional[Dict[str, Any]] = None,
        on_failure: Optional["HookSpecification"] = None,
        on_success: Optional["HookSpecification"] = None,
        merge: bool = True,
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
            name: DEPRECATED: The name of the step.
            enable_cache: If caching should be enabled for this step.
            enable_artifact_metadata: If artifact metadata should be enabled
                for this step.
            experiment_tracker: The experiment tracker to use for this step.
            step_operator: The step operator to use for this step.
            parameters: Function parameters for this step
            output_materializers: Output materializers for this step. If
                given as a dict, the keys must be a subset of the output names
                of this step. If a single value (type or string) is given, the
                materializer will be used for all outputs.
            output_artifacts: Output artifacts for this step. If
                given as a dict, the keys must be a subset of the output names
                of this step. If a single value (type or string) is given, the
                artifact class will be used for all outputs.
            settings: settings for this step.
            extra: Extra configurations for this step.
            on_failure: Callback function in event of failure of the step. Can be
                a function with three possible parameters, `StepContext`, `BaseParameters`,
                and `BaseException`, or a source path to a function of the same specifications
                (e.g. `module.my_function`)
            on_success: Callback function in event of failure of the step. Can be
                a function with two possible parameters, `StepContext` and `BaseParameters, or
                a source path to a function of the same specifications
                (e.g. `module.my_function`).
            merge: If `True`, will merge the given dictionary configurations
                like `parameters` and `settings` with existing
                configurations. If `False` the given configurations will
                overwrite all existing ones. See the general description of this
                method for an example.

        Returns:
            The step instance that this method was called on.
        """
        from zenml.hooks.hook_validators import resolve_and_validate_hook

        if name:
            logger.warning("Configuring the name of a step is deprecated.")

        def _resolve_if_necessary(
            value: Union[str, Source, Type[Any]]
        ) -> Source:
            if isinstance(value, str):
                return Source.from_import_path(value)
            elif isinstance(value, Source):
                return value
            else:
                return source_utils.resolve(value)

        outputs: Dict[str, Dict[str, Source]] = defaultdict(dict)
        allowed_output_names = set(self.OUTPUT_SIGNATURE)

        if output_materializers:
            if not isinstance(output_materializers, Mapping):
                # string of materializer class to be used for all outputs
                source = _resolve_if_necessary(output_materializers)
                output_materializers = {
                    output_name: source for output_name in allowed_output_names
                }

            for output_name, materializer in output_materializers.items():
                source = _resolve_if_necessary(materializer)
                outputs[output_name]["materializer_source"] = source

        failure_hook_source = None
        if on_failure:
            # string of on_failure hook function to be used for this step
            failure_hook_source = resolve_and_validate_hook(on_failure)

        success_hook_source = None
        if on_success:
            # string of on_success hook function to be used for this step
            success_hook_source = resolve_and_validate_hook(on_success)

        if output_artifacts:
            logger.warning(
                "The `output_artifacts` argument has no effect and will be "
                "removed in a future version."
            )

        if isinstance(parameters, BaseParameters):
            parameters = parameters.dict()

        values = dict_utils.remove_none_values(
            {
                "enable_cache": enable_cache,
                "enable_artifact_metadata": enable_artifact_metadata,
                "experiment_tracker": experiment_tracker,
                "step_operator": step_operator,
                "parameters": parameters,
                "settings": settings,
                "outputs": outputs or None,
                "extra": extra,
                "failure_hook_source": failure_hook_source,
                "success_hook_source": success_hook_source,
            }
        )
        config = StepConfigurationUpdate(**values)
        self._apply_configuration(config, merge=merge)
        return self

    def _apply_configuration(
        self,
        config: StepConfigurationUpdate,
        merge: bool = True,
    ) -> None:
        """Applies an update to the step configuration.

        Args:
            config: The configuration update.
            merge: Whether to merge the updates with the existing configuration
                or not. See the `BaseStep.configure(...)` method for a detailed
                explanation.
        """
        self._validate_configuration(config)

        self._configuration = pydantic_utils.update_model(
            self._configuration, update=config, recursive=merge
        )

        logger.debug("Updated step configuration:")
        logger.debug(self._configuration)

    def _validate_configuration(self, config: StepConfigurationUpdate) -> None:
        """Validates a configuration update.

        Args:
            config: The configuration update to validate.
        """
        settings_utils.validate_setting_keys(list(config.settings))
        self._validate_function_parameters(parameters=config.parameters)
        self._validate_outputs(outputs=config.outputs)

    def _validate_function_parameters(
        self, parameters: Dict[str, Any]
    ) -> None:
        """Validates step function parameters.

        Args:
            parameters: The parameters to validate.

        Raises:
            StepInterfaceError: If the step requires no function parameters but
                parameters were configured.
        """
        if not parameters:
            return

        signature = get_step_entrypoint_signature(step=self)
        for key, value in parameters.items():
            if key in signature.parameters:
                self._validate_parameter_value(
                    parameter=signature.parameters[key], value=value
                )
            elif not self.PARAMETERS_CLASS:
                raise StepInterfaceError(
                    "Can't set parameter without param class."
                )

    def _validate_outputs(
        self, outputs: Mapping[str, PartialArtifactConfiguration]
    ) -> None:
        """Validates the step output configuration.

        Args:
            outputs: The configured step outputs.

        Raises:
            StepInterfaceError: If an output for a non-existent name is
                configured of an output artifact/materializer source does not
                resolve to the correct class.
        """
        allowed_output_names = set(self.OUTPUT_SIGNATURE)
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
                if not source_utils.validate_source_class(
                    output.materializer_source, expected_class=BaseMaterializer
                ):
                    raise StepInterfaceError(
                        f"Materializer source `{output.materializer_source}` "
                        f"for output '{output_name}' of step '{self.name}' "
                        "does not resolve to a  `BaseMaterializer` subclass."
                    )

    def _validate_inputs(
        self,
        input_artifacts: Dict[str, _OutputArtifact],
        external_artifacts: Dict[str, UUID],
    ) -> None:
        signature = get_step_entrypoint_signature(step=self)
        for key in signature.parameters.keys():
            if (
                key in input_artifacts
                or key in self.configuration.parameters
                or key in external_artifacts
            ):
                continue
            raise StepInterfaceError(f"Missing entrypoint input {key}.")

    def _finalize_configuration(
        self,
        input_artifacts: Dict[str, _OutputArtifact],
        external_artifacts: Dict[str, UUID],
    ) -> StepConfiguration:
        """Finalizes the configuration after the step was called.

        Once the step was called, we know the outputs of previous steps
        and that no additional user configurations will be made. That means
        we can now collect the remaining artifact and materializer types
        as well as check for the completeness of the step function parameters.

        Args:
            input_artifacts: The input artifacts of this step.

        Returns:
            The finalized step configuration.

        Raises:
            StepInterfaceError: If an output does not have an explicit
                materializer assigned to it and there is no default
                materializer registered for the output type.
        """
        outputs: Dict[str, Dict[str, Source]] = defaultdict(dict)

        for output_name, output_annotation in self.OUTPUT_SIGNATURE.items():
            output = self._configuration.outputs.get(
                output_name, PartialArtifactConfiguration()
            )

            from pydantic.typing import (
                get_origin,
                is_none_type,
                is_union,
            )

            from zenml.steps.utils import get_args

            if not output.materializer_source:
                if output_annotation is Any:
                    raise StepInterfaceError(
                        "An explicit materializer needs to be specified for "
                        "step outputs with `Any` as type annotation.",
                        url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
                    )
                if is_union(
                    get_origin(output_annotation) or output_annotation
                ):
                    potential_types = [
                        type_
                        for type_ in get_args(output_annotation)
                        if not is_none_type(type_)
                    ]
                    if len(potential_types) == 1:
                        # Optional[], we just need a materializer for the one
                        # type
                        output_annotation = potential_types[0]
                    else:
                        # TODO: We should check if a materializer for each
                        # item in the Union
                        raise StepInterfaceError(
                            "An explicit materializer needs to be specified for "
                            "step outputs with `Union` as type annotation.",
                            url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
                        )

                if default_materializer_registry.is_registered(
                    output_annotation
                ):
                    materializer_class = default_materializer_registry[
                        output_annotation
                    ]
                else:
                    raise StepInterfaceError(
                        f"Unable to find materializer for output "
                        f"'{output_name}' of type `{output_annotation}` in step "
                        f"'{self.name}'. Please make sure to either "
                        f"explicitly set a materializer for step outputs "
                        f"using `step.configure(output_materializers=...)` or "
                        f"registering a default materializer for specific "
                        f"types by subclassing `BaseMaterializer` and setting "
                        f"its `ASSOCIATED_TYPES` class variable.",
                        url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
                    )
                outputs[output_name][
                    "materializer_source"
                ] = source_utils.resolve(materializer_class)

        parameters = self._finalize_parameters()
        self.configure(parameters=parameters, merge=False)
        self._validate_inputs(
            input_artifacts=input_artifacts,
            external_artifacts=external_artifacts,
        )

        values = dict_utils.remove_none_values({"outputs": outputs or None})
        config = StepConfigurationUpdate(**values)
        self._apply_configuration(config)

        self._configuration = self._configuration.copy(
            update={
                "caching_parameters": self.caching_parameters,
                "external_input_artifacts": external_artifacts,
            }
        )

        complete_configuration = StepConfiguration.parse_obj(
            self._configuration
        )
        return complete_configuration

    def _finalize_parameters(self) -> Dict[str, Any]:
        signature = get_step_entrypoint_signature(step=self)
        params = {
            key: value
            for key, value in self.configuration.parameters.items()
            if key in signature.parameters
        }

        if self.PARAMETERS_CLASS and self.PARAMETERS_FUNCTION_PARAMETER_NAME:
            legacy_params = self._finalize_legacy_parameters()
            params[self.PARAMETERS_FUNCTION_PARAMETER_NAME] = legacy_params

        # TODO: Should we treat pydantic classes special here and verify
        # that they can be instantiated?

        return params

    def _finalize_legacy_parameters(self) -> Dict[str, Any]:
        """Verifies and prepares the config parameters for running this step.

        When the step requires config parameters, this method:
            - checks if config parameters were set via a config object or file
            - tries to set missing config parameters from default values of the
              config class

        Returns:
            Values for the previously unconfigured function parameters.

        Raises:
            MissingStepParameterError: If no value could be found for one or
                more config parameters.
            StepInterfaceError: If the parameter class validation failed.
        """
        if not self.PARAMETERS_CLASS:
            return {}

        # parameters for the `BaseParameters` class specified in the "new" way
        # by specifying a dict of parameters for the
        # key `self.PARAMETERS_FUNCTION_PARAMETER_NAME`
        params_defined_in_new_way = (
            self.configuration.parameters.get(
                self.PARAMETERS_FUNCTION_PARAMETER_NAME
            )
            or {}
        )

        values = {}
        missing_keys = []
        for name, field in self.PARAMETERS_CLASS.__fields__.items():
            if name in self.configuration.parameters:
                # a value for this parameter has been set already
                values[name] = self.configuration.parameters[name]
            elif name in params_defined_in_new_way:
                # a value for this parameter has been set in the "new" way
                # already
                values[name] = params_defined_in_new_way[name]
            elif field.required:
                # this field has no default value set and therefore needs
                # to be passed via an initialized config object
                missing_keys.append(name)
            else:
                # use default value from the pydantic config class
                values[name] = field.default

        if missing_keys:
            raise MissingStepParameterError(
                self.name, missing_keys, self.PARAMETERS_CLASS
            )

        if self.PARAMETERS_CLASS.Config.extra == Extra.allow:
            # Add all parameters for the config class for backwards
            # compatibility if the config class allows extra attributes
            values.update(self.configuration.parameters)

        try:
            self.PARAMETERS_CLASS(**values)
        except ValidationError:
            raise StepInterfaceError("Failed to validate function parameters.")

        return values

    def _validate_parameter_value(
        self, parameter: inspect.Parameter, value: Any
    ) -> None:
        from pydantic.typing import get_origin, is_union

        from zenml.steps.utils import get_args

        expected_type = (
            get_origin(parameter.annotation) or parameter.annotation
        )

        if expected_type is Any:
            # Any type is allowed
            pass
        else:
            if is_union(expected_type):
                expected_type = get_args(parameter.annotation)
            elif issubclass(expected_type, BaseModel):
                # TODO: handle custom pydantic __root__ type here
                expected_type = (expected_type, dict)

            if not isinstance(value, expected_type):
                raise StepInterfaceError(
                    f"Wrong argument type (`{type(value)}`) for argument "
                    f"'{parameter.name}' of step '{self.name}'. The argument should "
                    f"either be an output of a previous steps or of type "
                    f"`{expected_type}`."
                )

        if not is_json_serializable(value):
            raise StepInterfaceError(
                f"Argument type (`{type(value)}`) for argument "
                f"'{parameter.name}' of step '{self.name}' is not JSON "
                "serializable."
            )


def is_json_serializable(obj: Any) -> bool:
    import json

    from pydantic.json import pydantic_encoder

    try:
        json.dumps(obj, default=pydantic_encoder)
        return True
    except TypeError:
        return False


def get_step_entrypoint_signature(
    step: "BaseStep", include_step_context: bool = False
) -> inspect.Signature:
    signature = inspect.signature(step.entrypoint, follow_wrapped=True)

    if include_step_context:
        return signature

    def _is_step_context_param(annotation: Any) -> bool:
        return inspect.isclass(annotation) and issubclass(
            annotation, StepContext
        )

    params_without_step_context = [
        param
        for param in signature.parameters.values()
        if not _is_step_context_param(param.annotation)
    ]

    signature = signature.replace(parameters=params_without_step_context)
    return signature


class StepInvocation:
    def __init__(
        self,
        id: str,
        step: "BaseStep",
        input_artifacts: Dict[str, BaseStep._OutputArtifact],
        external_artifacts: Dict[str, "ExternalArtifact"],
        parameters: Dict[str, Any],
        upstream_steps: Sequence[str],
    ) -> None:
        self.id = id
        self.step = step
        self.input_artifacts = input_artifacts
        self.external_artifacts = external_artifacts
        self.parameters = parameters
        self.invocation_upstream_steps = upstream_steps

    @property
    def upstream_steps(self) -> Set[str]:
        return self.step.upstream_steps.union(self.invocation_upstream_steps)

    def finalize(self) -> StepConfiguration:
        self.step.configure(parameters=self.parameters)

        external_artifact_ids = {}
        for key, artifact in self.external_artifacts.items():
            external_artifact_ids[key] = artifact.do_something()

        return self.step._finalize_configuration(
            input_artifacts=self.input_artifacts,
            external_artifacts=external_artifact_ids,
        )


import os


# StepArtifactSpec
# ExternalArtifactSpec
class StepArtifact:
    ...


class ExternalArtifact:
    def __init__(
        self,
        value: Any = None,
        id: Optional[UUID] = None,
        materializer: Optional["MaterializerClassOrSource"] = None,
    ) -> None:
        if value is not None and id is not None:
            raise ValueError("Only value or ID allowed")
        if value is None and id is None:
            raise ValueError("Either value or ID required")

        self._value = value
        self._id = id
        self._materializer = materializer

    def do_something(self) -> UUID:
        from uuid import uuid4

        from zenml.client import Client
        from zenml.io import fileio
        from zenml.models import ArtifactRequestModel

        artifact_store_id = Client().active_stack.artifact_store.id

        if self._id:
            response = Client().get_artifact(artifact_id=self._id)
            if response.artifact_store_id != artifact_store_id:
                raise RuntimeError("Artifact store mismatch")
        else:
            logger.info("Uploading external artifact.")
            client = Client()
            active_user_id = client.active_user.id
            active_workspace_id = client.active_workspace.id
            artifact_name = f"external_{uuid4()}"
            materializer_class = self._get_materializer()

            uri = os.path.join(
                Client().active_stack.artifact_store.path,
                "external_artifacts",
                artifact_name,
            )
            if fileio.exists(uri):
                raise RuntimeError("Artifact URI already exists")
            fileio.makedirs(uri)

            materializer = materializer_class(uri)
            materializer.save(self._value)

            artifact = ArtifactRequestModel(
                name=artifact_name,
                type=materializer_class.ASSOCIATED_ARTIFACT_TYPE,
                uri=uri,
                materializer=source_utils.resolve(materializer_class),
                data_type=source_utils.resolve(type(self._value)),
                user=active_user_id,
                workspace=active_workspace_id,
                artifact_store_id=artifact_store_id,
            )
            response = Client().zen_store.create_artifact(artifact=artifact)
            # To avoid duplicate uploads, switch to just referencing the
            # uploaded artifact
            self._value = None
            self._id = response.id

        return self._id

    def _get_materializer(self) -> Type["BaseMaterializer"]:
        assert self._value is not None

        if inspect.isclass(self._materializer):
            return self._materializer
        elif self._materializer:
            return source_utils.load_and_validate_class(
                self._materializer, expected_class=BaseMaterializer
            )
        else:
            value_type = type(self._value)
            if default_materializer_registry.is_registered(value_type):
                return default_materializer_registry[value_type]
            else:
                raise StepInterfaceError(
                    f"Unable to find materializer for type `{value_type}`. Please "
                    "make sure to either explicitly set a materializer for your "
                    "external artifact using "
                    "`ExternalArtifact(value=..., materializer=...)` or "
                    f"register a default materializer for specific "
                    f"types by subclassing `BaseMaterializer` and setting "
                    f"its `ASSOCIATED_TYPES` class variable.",
                    url="https://docs.zenml.io/advanced-guide/pipelines/materializers",
                )
