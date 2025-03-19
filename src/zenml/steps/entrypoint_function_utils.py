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
"""Util functions for step and pipeline entrypoint functions."""

import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    NamedTuple,
    NoReturn,
    Sequence,
    Type,
    Union,
)

from pydantic import ConfigDict, ValidationError, create_model

from zenml.constants import ENFORCE_TYPE_ANNOTATIONS
from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.metadata.lazy_load import LazyRunMetadataResponse
from zenml.steps.utils import (
    OutputSignature,
    parse_return_type_annotations,
    resolve_type_annotation,
)
from zenml.utils import yaml_utils

if TYPE_CHECKING:
    from zenml.config.source import Source
    from zenml.pipelines.pipeline_definition import Pipeline

    MaterializerClassOrSource = Union[str, "Source", Type["BaseMaterializer"]]

logger = get_logger(__name__)


class StepArtifact:
    """Class to represent step output artifacts."""

    def __init__(
        self,
        invocation_id: str,
        output_name: str,
        annotation: Any,
        pipeline: "Pipeline",
    ) -> None:
        """Initialize a step artifact.

        Args:
            invocation_id: The ID of the invocation that produces this artifact.
            output_name: The name of the output that produces this artifact.
            annotation: The output type annotation.
            pipeline: The pipeline which the invocation is part of.
        """
        self.invocation_id = invocation_id
        self.output_name = output_name
        self.annotation = annotation
        self.pipeline = pipeline

    def __iter__(self) -> NoReturn:
        """Raise a custom error if someone is trying to iterate this object.

        Raises:
            StepInterfaceError: If trying to iterate this object.
        """
        raise StepInterfaceError(
            "Unable to unpack step artifact. This error is probably because "
            "you're trying to unpack the return value of your step but the "
            "step only returns a single artifact. For more information on how "
            "to add type annotations to your step to indicate multiple "
            "artifacts visit https://docs.zenml.io/how-to/build-pipelines/step-output-typing-and-annotation#type-annotations."
        )


def validate_reserved_arguments(
    signature: inspect.Signature, reserved_arguments: Sequence[str]
) -> None:
    """Validates that the signature does not contain any reserved arguments.

    Args:
        signature: The signature to validate.
        reserved_arguments: The reserved arguments for the signature.

    Raises:
        RuntimeError: If the signature contains a reserved argument.
    """
    for arg in reserved_arguments:
        if arg in signature.parameters:
            raise RuntimeError(f"Reserved argument name '{arg}'.")


class EntrypointFunctionDefinition(NamedTuple):
    """Class representing a step entrypoint function.

    Attributes:
        inputs: The entrypoint function inputs.
        outputs: The entrypoint function outputs. This dictionary maps output
            names to output annotations.
    """

    inputs: Dict[str, inspect.Parameter]
    outputs: Dict[str, OutputSignature]

    def validate_input(self, key: str, value: Any) -> None:
        """Validates an input to the step entrypoint function.

        Args:
            key: The key for which the input was passed
            value: The input value.

        Raises:
            KeyError: If the function has no input for the given key.
            RuntimeError: If a parameter is passed for an input that is
                annotated as an `UnmaterializedArtifact`.
            RuntimeError: If the input value is not valid for the type
                annotation provided for the function parameter.
            StepInterfaceError: If the input is a parameter and not JSON
                serializable.
        """
        from zenml.artifacts.external_artifact import ExternalArtifact
        from zenml.artifacts.unmaterialized_artifact import (
            UnmaterializedArtifact,
        )
        from zenml.client_lazy_loader import ClientLazyLoader
        from zenml.models import ArtifactVersionResponse

        if key not in self.inputs:
            raise KeyError(
                f"Received step entrypoint input for invalid key {key}."
            )

        parameter = self.inputs[key]

        if isinstance(
            value,
            (
                StepArtifact,
                ExternalArtifact,
                ArtifactVersionResponse,
                ClientLazyLoader,
                LazyRunMetadataResponse,
            ),
        ):
            # If we were to do any type validation for artifacts here, we
            # would not be able to leverage pydantics type coercion (e.g.
            # providing an `int` artifact for a `float` input)
            return

        # Not an artifact -> This is a parameter
        if parameter.annotation is UnmaterializedArtifact:
            raise RuntimeError(
                "Passing parameter for input of type `UnmaterializedArtifact` "
                "is not allowed."
            )

        if not yaml_utils.is_json_serializable(value):
            raise StepInterfaceError(
                f"Argument type (`{type(value)}`) for argument "
                f"'{key}' is not JSON serializable and can not be passed as "
                "a parameter. This input can either be provided by the "
                "output of another step or as an external artifact: "
                "https://docs.zenml.io/user-guides/starter-guide/manage-artifacts#managing-artifacts-not-produced-by-zenml-pipelines"
            )

        try:
            self._validate_input_value(parameter=parameter, value=value)
        except ValidationError as e:
            raise RuntimeError(
                f"Input validation failed for input '{parameter.name}': "
                f"Expected type `{parameter.annotation}` but received type "
                f"`{type(value)}`."
            ) from e

    def _validate_input_value(
        self, parameter: inspect.Parameter, value: Any
    ) -> None:
        """Validates an input value to the step entrypoint function.

        Args:
            parameter: The function parameter for which the value was provided.
            value: The input value.
        """
        # We allow passing None for optional annotations that would otherwise
        # not be allowed as a parameter
        config_dict = ConfigDict(arbitrary_types_allowed=value is None)

        # Create a pydantic model with just a single required field with the
        # type annotation of the parameter to verify the input type including
        # pydantics type coercion
        validation_model_class = create_model(
            "input_validation_model",
            __config__=config_dict,
            value=(parameter.annotation, ...),
        )
        validation_model_class(value=value)


def validate_entrypoint_function(
    func: Callable[..., Any],
    reserved_arguments: Sequence[str] = (),
) -> EntrypointFunctionDefinition:
    """Validates a step entrypoint function.

    Args:
        func: The step entrypoint function to validate.
        reserved_arguments: The reserved arguments for the entrypoint function.

    Raises:
        StepInterfaceError: If the entrypoint function has variable arguments
            or keyword arguments.
        RuntimeError: If type annotations should be enforced and a type
            annotation is missing.

    Returns:
        A validated definition of the entrypoint function.
    """
    signature = inspect.signature(func, follow_wrapped=True)
    validate_reserved_arguments(
        signature=signature, reserved_arguments=reserved_arguments
    )

    inputs = {}

    signature_parameters = list(signature.parameters.items())
    for key, parameter in signature_parameters:
        if parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}:
            raise StepInterfaceError(
                f"Variable args or kwargs not allowed for function "
                f"{func.__name__}."
            )

        annotation = parameter.annotation
        if annotation is parameter.empty:
            if ENFORCE_TYPE_ANNOTATIONS:
                raise RuntimeError(
                    f"Missing type annotation for input '{key}' of step "
                    f"function '{func.__name__}'."
                )

            # If a type annotation is missing, use `Any` instead
            parameter = parameter.replace(annotation=Any)

        annotation = resolve_type_annotation(annotation)
        inputs[key] = parameter

    outputs = parse_return_type_annotations(
        func=func,
        enforce_type_annotations=ENFORCE_TYPE_ANNOTATIONS,
    )

    return EntrypointFunctionDefinition(
        inputs=inputs,
        outputs=outputs,
    )
