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

"""Utility functions and classes to run ZenML steps."""

import ast
import contextlib
import inspect
import textwrap
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple, Union
from uuid import UUID

from pydantic import BaseModel
from typing_extensions import Annotated

from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.client import Client
from zenml.enums import (
    ArtifactSaveType,
    ExecutionStatus,
    MetadataResourceTypes,
)
from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.steps.step_context import get_step_context
from zenml.utils import settings_utils, source_code_utils, typing_utils

if TYPE_CHECKING:
    from zenml.steps import BaseStep


logger = get_logger(__name__)

SINGLE_RETURN_OUT_NAME = "output"


class OutputSignature(BaseModel):
    """The signature of an output artifact."""

    resolved_annotation: Any = None
    artifact_config: Optional[ArtifactConfig] = None
    has_custom_name: bool = False

    def get_output_types(self) -> Tuple[Any, ...]:
        """Get all output types that match the type annotation.

        Returns:
            All output types that match the type annotation.
        """
        if self.resolved_annotation is Any:
            return ()

        if typing_utils.is_union(
            typing_utils.get_origin(self.resolved_annotation)
            or self.resolved_annotation
        ):
            return tuple(
                type(None)
                if typing_utils.is_none_type(output_type)
                else output_type
                for output_type in get_args(self.resolved_annotation)
            )
        else:
            return (self.resolved_annotation,)


def get_args(obj: Any) -> Tuple[Any, ...]:
    """Get arguments of a type annotation.

    Example:
        `get_args(Union[int, str]) == (int, str)`

    Args:
        obj: The annotation.

    Returns:
        The args of the annotation.
    """
    return tuple(
        typing_utils.get_origin(v) or v for v in typing_utils.get_args(obj)
    )


def parse_return_type_annotations(
    func: Callable[..., Any], enforce_type_annotations: bool = False
) -> Dict[str, OutputSignature]:
    """Parse the return type annotation of a step function.

    Args:
        func: The step function.
        enforce_type_annotations: If `True`, raises an exception if a type
            annotation is missing.

    Raises:
        RuntimeError: If the output annotation has variable length or contains
            duplicate output names.
        RuntimeError: If type annotations should be enforced and a type
            annotation is missing.

    Returns:
        - A dictionary mapping output names to their output signatures.
    """
    signature = inspect.signature(func, follow_wrapped=True)
    return_annotation = signature.return_annotation
    output_name: Optional[str]

    # Return type annotated as `None`
    if return_annotation is None:
        return {}

    # Return type not annotated -> check whether `None` or `Any` should be used
    if return_annotation is signature.empty:
        if enforce_type_annotations:
            raise RuntimeError(
                "Missing return type annotation for step function "
                f"'{func.__name__}'."
            )
        elif has_only_none_returns(func):
            return {}
        else:
            return_annotation = Any

    if typing_utils.get_origin(return_annotation) is tuple:
        requires_multiple_artifacts = has_tuple_return(func)
        if requires_multiple_artifacts:
            output_signature: Dict[str, Any] = {}
            args = typing_utils.get_args(return_annotation)
            if args[-1] is Ellipsis:
                raise RuntimeError(
                    "Variable length output annotations are not allowed."
                )
            for i, annotation in enumerate(args):
                resolved_annotation = resolve_type_annotation(annotation)
                artifact_config = get_artifact_config_from_annotation_metadata(
                    annotation
                )
                output_name = artifact_config.name if artifact_config else None
                has_custom_name = output_name is not None
                output_name = output_name or f"output_{i}"
                if output_name in output_signature:
                    raise RuntimeError(f"Duplicate output name {output_name}.")

                output_signature[output_name] = OutputSignature(
                    resolved_annotation=resolved_annotation,
                    artifact_config=artifact_config,
                    has_custom_name=has_custom_name,
                )
            return output_signature

    # Return type is annotated as single value or is a tuple
    resolved_annotation = resolve_type_annotation(return_annotation)
    artifact_config = get_artifact_config_from_annotation_metadata(
        return_annotation
    )
    output_name = artifact_config.name if artifact_config else None
    has_custom_name = output_name is not None
    output_name = output_name or SINGLE_RETURN_OUT_NAME
    return {
        output_name: OutputSignature(
            resolved_annotation=resolved_annotation,
            artifact_config=artifact_config,
            has_custom_name=has_custom_name,
        )
    }


def resolve_type_annotation(obj: Any) -> Any:
    """Returns the non-generic class for generic aliases of the typing module.

    Example: if the input object is `typing.Dict`, this method will return the
    concrete class `dict`.

    Args:
        obj: The object to resolve.

    Returns:
        The non-generic class for generic aliases of the typing module.
    """
    origin = typing_utils.get_origin(obj) or obj

    if origin is Annotated:
        annotation, *_ = typing_utils.get_args(obj)
        return resolve_type_annotation(annotation)
    elif typing_utils.is_union(origin):
        return obj

    return origin


def get_artifact_config_from_annotation_metadata(
    annotation: Any,
) -> Optional[ArtifactConfig]:
    """Get the artifact config from the annotation metadata of a step output.

    Example:
    ```python
    get_output_name_from_annotation_metadata(int)  # None
    get_output_name_from_annotation_metadata(Annotated[int, "name"]  # ArtifactConfig(name="name")
    get_output_name_from_annotation_metadata(Annotated[int, ArtifactConfig(name="name", model_name="foo")]  # ArtifactConfig(name="name", model_name="foo")
    ```

    Args:
        annotation: The type annotation.

    Raises:
        ValueError: If the annotation is not following the expected format
            or if the name was specified multiple times or is an empty string.

    Returns:
        The artifact config.
    """
    if (typing_utils.get_origin(annotation) or annotation) is not Annotated:
        return None

    annotation, *metadata = typing_utils.get_args(annotation)

    error_message = (
        "Artifact annotation should only contain two elements: the artifact "
        "type, and either an output name or an `ArtifactConfig`, e.g.: "
        "`Annotated[int, 'output_name']` or "
        "`Annotated[int, ArtifactConfig(name='output_name'), ...]`."
    )

    if len(metadata) > 2:
        raise ValueError(error_message)

    # Loop over all values to also support legacy annotations of the form
    # `Annotated[int, 'output_name', ArtifactConfig(...)]`
    output_name = None
    artifact_config = None
    for metadata_instance in metadata:
        if isinstance(metadata_instance, str):
            if output_name is not None:
                raise ValueError(error_message)
            output_name = metadata_instance
        elif isinstance(metadata_instance, ArtifactConfig):
            if artifact_config is not None:
                raise ValueError(error_message)
            artifact_config = metadata_instance
        else:
            raise ValueError(error_message)

    # Consolidate output name
    if artifact_config and artifact_config.name:
        if output_name is not None:
            raise ValueError(error_message)
    elif output_name:
        if not artifact_config:
            artifact_config = ArtifactConfig(name=output_name)
        elif not artifact_config.name:
            artifact_config = artifact_config.model_copy()
            artifact_config.name = output_name

    if artifact_config and artifact_config.name == "":
        raise ValueError("Output name cannot be an empty string.")

    return artifact_config


class ReturnVisitor(ast.NodeVisitor):
    """AST visitor class that can be subclassed to visit function returns."""

    def __init__(self, ignore_nested_functions: bool = True) -> None:
        """Initializes a return visitor instance.

        Args:
            ignore_nested_functions: If `True`, will skip visiting nested
                functions.
        """
        self._ignore_nested_functions = ignore_nested_functions
        self._inside_function = False

    def _visit_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """Visit a (async) function definition node.

        Args:
            node: The node to visit.
        """
        if self._ignore_nested_functions and self._inside_function:
            # We're already inside a function definition and should ignore
            # nested functions so we don't want to recurse any further
            return

        self._inside_function = True
        self.generic_visit(node)

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function


class OnlyNoneReturnsVisitor(ReturnVisitor):
    """Checks whether a function AST contains only `None` returns."""

    def __init__(self) -> None:
        """Initializes a visitor instance."""
        super().__init__()
        self.has_only_none_returns = True

    def visit_Return(self, node: ast.Return) -> None:
        """Visit a return statement.

        Args:
            node: The return statement to visit.
        """
        if node.value is not None:
            if isinstance(node.value, (ast.Constant, ast.NameConstant)):
                if node.value.value is None:
                    return

            self.has_only_none_returns = False


class TupleReturnVisitor(ReturnVisitor):
    """Checks whether a function AST contains tuple returns."""

    def __init__(self) -> None:
        """Initializes a visitor instance."""
        super().__init__()
        self.has_tuple_return = False

    def visit_Return(self, node: ast.Return) -> None:
        """Visit a return statement.

        Args:
            node: The return statement to visit.
        """
        if isinstance(node.value, ast.Tuple) and len(node.value.elts) > 1:
            self.has_tuple_return = True


def has_tuple_return(func: Callable[..., Any]) -> bool:
    """Checks whether a function returns multiple values.

    Multiple values means that the `return` statement is followed by a tuple
    (with or without brackets).

    Example:
    ```python
    def f1():
      return 1, 2

    def f2():
      return (1, 2)

    def f3():
      var = (1, 2)
      return var

    has_tuple_return(f1)  # True
    has_tuple_return(f2)  # True
    has_tuple_return(f3)  # False
    ```

    Args:
        func: The function to check.

    Returns:
        Whether the function returns multiple values.
    """
    source = textwrap.dedent(source_code_utils.get_source_code(func))
    tree = ast.parse(source)

    visitor = TupleReturnVisitor()
    visitor.visit(tree)

    return visitor.has_tuple_return


def has_only_none_returns(func: Callable[..., Any]) -> bool:
    """Checks whether a function contains only `None` returns.

    A `None` return could be either an explicit `return None` or an empty
    `return` statement.

    Example:
    ```python
    def f1():
      return None

    def f2():
      return

    def f3(condition):
      if condition:
        return None
      else:
        return 1

    has_only_none_returns(f1)  # True
    has_only_none_returns(f2)  # True
    has_only_none_returns(f3)  # False
    ```

    Args:
        func: The function to check.

    Returns:
        Whether the function contains only `None` returns.
    """
    source = textwrap.dedent(source_code_utils.get_source_code(func))
    tree = ast.parse(source)

    visitor = OnlyNoneReturnsVisitor()
    visitor.visit(tree)

    return visitor.has_only_none_returns


def log_step_metadata(
    metadata: Dict[str, "MetadataType"],
    step_name: Optional[str] = None,
    pipeline_name_id_or_prefix: Optional[Union[str, UUID]] = None,
    run_id: Optional[str] = None,
) -> None:
    """Logs step metadata.

    Args:
        metadata: The metadata to log.
        step_name: The name of the step to log metadata for. Can be omitted
            when being called inside a step.
        pipeline_name_id_or_prefix: The name of the pipeline to log metadata
            for. Can be omitted when being called inside a step.
        run_id: The ID of the run to log metadata for. Can be omitted when
            being called inside a step.

    Raises:
        ValueError: If no step name is provided and the function is not called
            from within a step or if no pipeline name or ID is provided and
            the function is not called from within a step.
    """
    logger.warning(
        "The `log_step_metadata` function is deprecated and will soon be "
        "removed. Please use `log_metadata` instead."
    )

    step_context = None
    if not step_name:
        with contextlib.suppress(RuntimeError):
            step_context = get_step_context()
            step_name = step_context.step_name
    # not running within a step and no user-provided step name
    if not step_name:
        raise ValueError(
            "No step name provided and you are not running "
            "within a step. Please provide a step name."
        )

    client = Client()
    if step_context:
        step_run_id = step_context.step_run.id
    elif run_id:
        step_run_id = UUID(int=int(run_id))
    else:
        if not pipeline_name_id_or_prefix:
            raise ValueError(
                "No pipeline name or ID provided and you are not running "
                "within a step. Please provide a pipeline name or ID, or "
                "provide a run ID."
            )
        pipeline_run = client.get_pipeline(
            name_id_or_prefix=pipeline_name_id_or_prefix,
        ).last_run
        step_run_id = pipeline_run.steps[step_name].id
    client.create_run_metadata(
        metadata=metadata,
        resource_id=step_run_id,
        resource_type=MetadataResourceTypes.STEP_RUN,
    )


def run_as_single_step_pipeline(
    __step: "BaseStep", *args: Any, **kwargs: Any
) -> Any:
    """Runs the step as a single step pipeline.

    - All inputs that are not JSON serializable will be uploaded to the
    artifact store before the pipeline is being executed.
    - All output artifacts of the step will be loaded using the materializer
    that was used to store them.

    Args:
        *args: Entrypoint function arguments.
        **kwargs: Entrypoint function keyword arguments.

    Raises:
        RuntimeError: If the step execution failed.
        StepInterfaceError: If the arguments to the entrypoint function are
            invalid.

    Returns:
        The output of the step entrypoint function.
    """
    from zenml import ExternalArtifact, pipeline
    from zenml.config.base_settings import BaseSettings
    from zenml.pipelines.run_utils import (
        wait_for_pipeline_run_to_finish,
    )

    logger.info(
        "Running single step pipeline to execute step `%s`", __step.name
    )

    try:
        validated_arguments = (
            inspect.signature(__step.entrypoint)
            .bind(*args, **kwargs)
            .arguments
        )
    except TypeError as e:
        raise StepInterfaceError(
            "Invalid step function entrypoint arguments. Check out the "
            "error above for more details."
        ) from e

    inputs: Dict[str, Any] = {}
    for key, value in validated_arguments.items():
        try:
            __step.entrypoint_definition.validate_input(key=key, value=value)
            inputs[key] = value
        except Exception:
            inputs[key] = ExternalArtifact(value=value)

    orchestrator = Client().active_stack.orchestrator

    pipeline_settings: Any = {}
    if "synchronous" in orchestrator.config.model_fields:
        # Make sure the orchestrator runs sync so we stream the logs
        key = settings_utils.get_stack_component_setting_key(orchestrator)
        pipeline_settings[key] = BaseSettings(synchronous=True)

    @pipeline(name=__step.name, enable_cache=False, settings=pipeline_settings)
    def single_step_pipeline() -> None:
        __step(**inputs)

    run = single_step_pipeline.with_options(unlisted=True)()
    assert run
    run = wait_for_pipeline_run_to_finish(run.id)

    if run.status != ExecutionStatus.COMPLETED:
        raise RuntimeError("Failed to execute step %s.", __step.name)

    # 4. Load output artifacts
    step_run = next(iter(run.steps.values()))
    outputs = [
        artifact_version.load()
        for output_name in step_run.config.outputs.keys()
        for artifact_version in step_run.outputs[output_name]
        if artifact_version.save_type == ArtifactSaveType.STEP_OUTPUT
    ]

    if len(outputs) == 0:
        return None
    elif len(outputs) == 1:
        return outputs[0]
    else:
        return tuple(outputs)
