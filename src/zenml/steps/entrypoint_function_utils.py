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
import inspect
import json
import os
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel
from pydantic.json import pydantic_encoder

from zenml.exceptions import StepInterfaceError
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.materializer_registry import materializer_registry
from zenml.steps.utils import parse_return_type_annotations
from zenml.utils import artifact_utils, source_utils

if TYPE_CHECKING:
    from zenml.config.source import Source
    from zenml.new.pipelines.pipeline import Pipeline
    from zenml.steps import BaseStep

    MaterializerClassOrSource = Union[str, "Source", Type["BaseMaterializer"]]

logger = get_logger(__name__)


def is_json_serializable(obj: Any) -> bool:
    try:
        json.dumps(obj, default=pydantic_encoder)
        return True
    except TypeError:
        return False


def get_step_entrypoint_signature(
    step: "BaseStep", include_step_context: bool = False
) -> inspect.Signature:
    from zenml.steps import StepContext

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


class Artifact:
    pass


class StepArtifact(Artifact):
    def __init__(
        self,
        invocation_id: str,
        output_name: str,
        annotation: Any,
        pipeline: "Pipeline",
    ) -> None:
        self.invocation_id = invocation_id
        self.output_name = output_name
        self.annotation = annotation
        self.pipeline = pipeline


class ExternalArtifact(Artifact):
    def __init__(
        self,
        value: Any = None,
        id: Optional[UUID] = None,
        materializer: Optional["MaterializerClassOrSource"] = None,
        store_artifact_metadata: bool = True,
        store_artifact_visualizations: bool = True,
    ) -> None:
        if value is not None and id is not None:
            raise ValueError("Only value or ID allowed")
        if value is None and id is None:
            raise ValueError("Either value or ID required")

        self._value = value
        self._id = id
        self._materializer = materializer
        self._store_artifact_metadata = store_artifact_metadata
        self._store_artifact_visualizations = store_artifact_visualizations

    def upload_if_necessary(self) -> UUID:
        from uuid import uuid4

        from zenml.client import Client
        from zenml.io import fileio

        artifact_store_id = Client().active_stack.artifact_store.id

        if self._id:
            response = Client().get_artifact(artifact_id=self._id)
            if response.artifact_store_id != artifact_store_id:
                raise RuntimeError("Artifact store mismatch")
        else:
            logger.info("Uploading external artifact.")
            artifact_name = f"external_{uuid4()}"
            materializer_class = self._get_materializer()

            uri = os.path.join(
                Client().active_stack.artifact_store.path,
                "external_artifacts",
                artifact_name,
            )
            if fileio.exists(uri):
                raise RuntimeError(f"Artifact URI {uri} already exists.")
            fileio.makedirs(uri)

            materializer = materializer_class(uri)

            artifact, metadata = artifact_utils.upload_artifact(
                name=artifact_name,
                data=self._value,
                materializer=materializer,
                artifact_store_id=artifact_store_id,
                extract_metadata=self._store_artifact_metadata,
                include_visualizations=self._store_artifact_visualizations,
            )
            response = Client().zen_store.create_artifact(artifact=artifact)
            if metadata:
                Client().create_run_metadata(
                    metadata=metadata, artifact_id=response.id
                )

            # To avoid duplicate uploads, switch to just referencing the
            # uploaded artifact
            self._id = response.id

        return self._id

    def _get_materializer(self) -> Type["BaseMaterializer"]:
        assert self._value is not None

        if isinstance(self._materializer, type):
            return self._materializer
        elif self._materializer:
            return source_utils.load_and_validate_class(
                self._materializer, expected_class=BaseMaterializer
            )
        else:
            type_ = type(self._value)
            return materializer_registry[type_]


def validate_reserved_arguments(
    signature: inspect.Signature, reserved_arguments: Sequence[str]
) -> None:
    for arg in reserved_arguments:
        if arg in signature.parameters:
            raise RuntimeError(f"Reserved argument name {arg}.")


class EntrypointFunctionDefinition(NamedTuple):
    inputs: Dict[str, inspect.Parameter]
    outputs: Dict[str, Any]
    context: Optional[inspect.Parameter]
    params: Optional[inspect.Parameter]

    def validate_input(
        self,
        key: str,
        input_: Union["Artifact", Any],
    ) -> None:
        from zenml.materializers import UnmaterializedArtifact

        if key not in self.inputs:
            raise KeyError(f"No input for key {key}.")

        parameter = self.inputs[key]

        if isinstance(input_, Artifact):
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

        self._validate_input_value(parameter=parameter, value=input_)

        if not is_json_serializable(input_):
            raise StepInterfaceError(
                f"Argument type (`{type(input_)}`) for argument "
                f"'{key}' is not JSON "
                "serializable."
            )

    def _validate_input_value(
        self, parameter: inspect.Parameter, value: Any
    ) -> None:
        from pydantic import BaseConfig, ValidationError, create_model

        class ModelConfig(BaseConfig):
            arbitrary_types_allowed = False

        # Create a pydantic model with just a single required field with the
        # type annotation of the parameter to verify the input type including
        # pydantics type coercion
        validation_model_class = create_model(
            "input_validation_model",
            __config__=ModelConfig,
            value=(parameter.annotation, ...),
        )

        try:
            validation_model_class(value=value)
        except ValidationError as e:
            raise RuntimeError("Input validation failed.") from e

    def _validate_input_type(
        self, parameter: inspect.Parameter, annotation: Any
    ) -> None:

        from pydantic.typing import get_origin, is_union

        from zenml.steps.utils import get_args

        def _get_allowed_types(annotation: Any) -> Tuple[Any, ...]:
            origin = get_origin(annotation) or annotation
            if is_union(origin):
                allowed_types = get_args(annotation)
            elif inspect.isclass(annotation) and issubclass(
                annotation, BaseModel
            ):
                if annotation.__custom_root_type__:
                    allowed_types = (annotation,) + _get_allowed_types(
                        annotation.__fields__["__root__"].outer_type_
                    )
                else:
                    allowed_types = (annotation, dict)
            else:
                allowed_types = (origin,)

            return allowed_types

        allowed_types = _get_allowed_types(annotation=parameter.annotation)
        input_types = _get_allowed_types(annotation=annotation)

        if Any in input_types or Any in allowed_types:
            # Skip type checks for `Any` annotations
            return

        for type_ in input_types:
            if not issubclass(type_, allowed_types):
                raise StepInterfaceError(
                    f"Wrong input type (`{annotation}`) for argument "
                    f"'{parameter.name}'. The argument "
                    f"should be of type `{parameter.annotation}`."
                )


def validate_entrypoint_function(
    func: Callable[..., Any], reserved_arguments: Sequence[str] = ()
) -> EntrypointFunctionDefinition:
    from zenml.steps import BaseParameters, StepContext

    signature = inspect.signature(func, follow_wrapped=True)
    validate_reserved_arguments(
        signature=signature, reserved_arguments=reserved_arguments
    )

    inputs = {}
    context: Optional[inspect.Parameter] = None
    params: Optional[inspect.Parameter] = None

    for key, parameter in signature.parameters.items():
        if parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}:
            raise StepInterfaceError(
                f"Variable args or kwargs not allowed for function {func.__name__}."
            )

        annotation = parameter.annotation
        if annotation is parameter.empty:
            raise StepInterfaceError(
                f"Missing type annotation for argument '{key}'. Please make "
                "sure to include type annotations for all your step inputs "
                f"and outputs."
            )

        if inspect.isclass(annotation) and issubclass(
            annotation, BaseParameters
        ):
            if params is not None:
                raise StepInterfaceError(
                    f"Found multiple parameter arguments "
                    f"('{params.name}' and '{key}') "
                    f"for function {func.__name__}."
                )
            params = parameter

        elif inspect.isclass(annotation) and issubclass(
            annotation, StepContext
        ):
            if context is not None:
                raise StepInterfaceError(
                    f"Found multiple context arguments "
                    f"('{context.name}' and '{key}') "
                    f"for function {func.__name__}."
                )
            context = parameter
        else:
            inputs[key] = parameter

    if signature.return_annotation is signature.empty:
        raise StepInterfaceError(
            f"Missing return type annotation for function {func.__name__}."
        )

    outputs = parse_return_type_annotations(
        return_annotation=signature.return_annotation
    )

    return EntrypointFunctionDefinition(
        inputs=inputs, outputs=outputs, context=context, params=params
    )
