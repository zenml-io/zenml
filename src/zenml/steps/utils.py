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

import typing
from typing import Annotated, Any, Callable, Dict, Optional, Tuple

import pydantic.typing as pydantic_typing

from zenml.logger import get_logger
from zenml.steps.step_output import Output

logger = get_logger(__name__)

SINGLE_RETURN_OUT_NAME = "output"


def resolve_type_annotation(obj: Any) -> Any:
    """Returns the non-generic class for generic aliases of the typing module.

    If the input is no generic typing alias, the input itself is returned.

    Example: if the input object is `typing.Dict`, this method will return the
    concrete class `dict`.

    Args:
        obj: The object to resolve.

    Returns:
        The non-generic class for generic aliases of the typing module.
    """
    origin = pydantic_typing.get_origin(obj) or obj

    if pydantic_typing.is_union(origin):
        return obj

    return origin


def get_args(obj: Any) -> Tuple[Any, ...]:
    """Get arguments of a Union type annotation.

    Example:
        `get_args(Union[int, str]) == (int, str)`

    Args:
        obj: The annotation.

    Returns:
        The args of the Union annotation.
    """
    return tuple(
        pydantic_typing.get_origin(v) or v
        for v in pydantic_typing.get_args(obj)
    )


def parse_return_type_annotations(return_annotation: Any) -> Dict[str, Any]:
    """Parse the returns of a step function into a dict of resolved types.

    Called within `BaseStepMeta.__new__()` to define `cls.OUTPUT_SIGNATURE`.

    Args:
        return_annotation: Return annotation of the step function.

    Returns:
        Output signature of the new step class.
    """
    if return_annotation is None:
        return {}

    # Cast simple output types to `Output`.
    if not isinstance(return_annotation, Output):
        return_annotation = Output(
            **{SINGLE_RETURN_OUT_NAME: return_annotation}
        )

    # Resolve type annotations of all outputs and save in new dict.
    output_signature = {
        output_name: resolve_type_annotation(output_type)
        for output_name, output_type in return_annotation.items()
    }
    return output_signature


def new_parse_return_type_annotations(
    func: Callable[..., Any], strict: bool = False
) -> Dict[str, Any]:
    signature = inspect.signature(func, follow_wrapped=True)
    return_annotation = signature.return_annotation

    if return_annotation is None:
        return {}

    if return_annotation is signature.empty:
        if has_only_none_returns(func):
            return {}
        else:
            return_annotation = Any

    if isinstance(return_annotation, Output):
        return {
            output_name: resolve_type_annotation(output_type)
            for output_name, output_type in return_annotation.items()
        }
    elif pydantic_typing.get_origin(return_annotation) is tuple:
        # TODO: should we also enter this for `Annotated[Tuple[...], ...]`?
        requires_multiple_artifacts = has_tuple_return(func)

        if requires_multiple_artifacts:
            output_signature = {}

            args = typing.get_args(return_annotation)
            if args[-1] is Ellipsis:
                raise RuntimeError(
                    "Variable length output annotations are not allowed."
                )

            for i, annotation in enumerate(args):
                resolved_annotation, output_name = new_resolve_type_annotation(
                    annotation
                )
                output_name = output_name or f"output_{i}"
                if output_name in output_signature:
                    raise RuntimeError("Duplicate output name")

                output_signature[output_name] = resolved_annotation

            return output_signature

    resolved_annotation, output_name = new_resolve_type_annotation(
        return_annotation
    )
    output_signature = {
        output_name or SINGLE_RETURN_OUT_NAME: resolved_annotation
    }

    return output_signature


def new_resolve_type_annotation(obj: Any) -> Tuple[Any, Optional[str]]:
    origin = pydantic_typing.get_origin(obj) or obj

    if origin is Annotated:
        annotation, *_ = typing.get_args(obj)
        output_name = validate_annotation_metadata(obj)

        resolved_annotation, _ = new_resolve_type_annotation(annotation)
        return resolved_annotation, output_name

    elif pydantic_typing.is_union(origin):
        return obj, None

    return origin, None


def validate_annotation_metadata(annotation: Any) -> str:
    annotation, *metadata = typing.get_args(annotation)

    if len(metadata) != 1:
        raise ValueError(
            "Annotation metadata can only contain a single element which must be the output name."
        )

    output_name = metadata[0]

    if not isinstance(output_name, str):
        raise ValueError(
            "Annotation metadata must be a string which will be used as the output name."
        )

    return output_name


import ast
import inspect
import textwrap
from typing import Any, Callable, Union


class ReturnVisitor(ast.NodeVisitor):
    def __init__(self, ignore_nested_functions: bool = True) -> None:
        self._ignore_nested_functions = ignore_nested_functions
        self._inside_function = False

    def _visit_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> Any:
        if self._ignore_nested_functions and self._inside_function:
            # We're already inside a function definition and should ignore
            # nested functions so we don't want to recurse any further
            return

        self._inside_function = True
        self.generic_visit(node)

    visit_FunctionDef = _visit_function
    visit_AsyncFunctionDef = _visit_function


class OnlyNoneReturnsVisitor(ReturnVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.has_only_none_returns = True

    def visit_Return(self, node: ast.Return) -> Any:
        if node.value is not None:
            if isinstance(node.value, (ast.Constant, ast.NameConstant)):
                if node.value.value is None:
                    return

            self.has_only_none_returns = False


class TupleReturnVisitor(ReturnVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.has_tuple_return = False

    def visit_Return(self, node: ast.Return) -> Any:
        if isinstance(node.value, ast.Tuple) and len(node.value.elts) > 1:
            self.has_tuple_return = True


def has_tuple_return(func: Callable[..., Any]) -> bool:
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)

    visitor = TupleReturnVisitor()
    visitor.visit(tree)

    return visitor.has_tuple_return


def has_only_none_returns(func: Callable[..., Any]) -> bool:
    source = textwrap.dedent(inspect.getsource(func))
    tree = ast.parse(source)

    visitor = OnlyNoneReturnsVisitor()
    visitor.visit(tree)

    return visitor.has_only_none_returns
