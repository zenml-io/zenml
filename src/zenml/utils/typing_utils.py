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
"""Carried over version of some functions from the pydantic v1 typing module.

Check out the latest version here:
https://github.com/pydantic/pydantic/blob/v1.10.14/pydantic/typing.py
"""

import typing
from typing import Any, Union, cast
from typing import get_args as _typing_get_args
from typing import get_origin as _typing_get_origin

from typing import Annotated, Literal

# Annotated[...] is implemented by returning an instance of one of these
# classes, depending on python/typing_extensions version.
AnnotatedTypeNames = {"AnnotatedMeta", "_AnnotatedAlias"}

# None types
NONE_TYPES: tuple[Any, Any, Any] = (None, None.__class__, Literal[None])

# Literal types
LITERAL_TYPES: set[Any] = {Literal}
if hasattr(typing, "Literal"):
    LITERAL_TYPES.add(typing.Literal)

# ----- is_none_type -----


def is_none_type(type_: Any) -> bool:
    """Checks if the provided type is a none type.

    Args:
        type_: type to check.

    Returns:
        boolean indicating whether the type is a none type.
    """
    return type_ in NONE_TYPES


# ----- is_union -----


def is_union(type_: type[Any] | None) -> bool:
    """Checks if the provided type is a union type.

        Args:
            type_: type to check.

        Returns:
            boolean indicating whether the type is union type.
        """
    import types

    return type_ is Union or type_ is types.UnionType  # type: ignore[comparison-overlap]


# ----- literal -----


def is_literal_type(type_: type[Any]) -> bool:
    """Checks if the provided type is a literal type.

    Args:
        type_: type to check.

    Returns:
        boolean indicating whether the type is union type.
    """
    return Literal is not None and get_origin(type_) in LITERAL_TYPES


def literal_values(type_: type[Any]) -> tuple[Any, ...]:
    """Fetches the literal values defined in a type.

    Args:
        type_: type to check.

    Returns:
        tuple of the literal values.
    """
    return get_args(type_)


def all_literal_values(type_: type[Any]) -> tuple[Any, ...]:
    """Fetches the literal values defined in a type in a recursive manner.

    This method is used to retrieve all Literal values as Literal can be
    used recursively (see https://www.python.org/dev/peps/pep-0586)
    e.g. `Literal[Literal[Literal[1, 2, 3], "foo"], 5, None]`

    Args:
        type_: type to check.

    Returns:
        tuple of all the literal values defined in the type.
    """
    if not is_literal_type(type_):
        return (type_,)

    values = literal_values(type_)
    return tuple(x for value in values for x in all_literal_values(value))


# ----- get_origin -----


def get_origin(tp: type[Any]) -> type[Any] | None:
    """Fetches the origin of a given type.

    We can't directly use `typing.get_origin` since we need a fallback to
    support custom generic classes like `ConstrainedList`
    It should be useless once https://github.com/cython/cython/issues/3537 is
    solved and https://github.com/pydantic/pydantic/pull/1753 is merged.

    Args:
        tp: type to check

    Returns:
        the origin type of the provided type.
    """
    if type(tp).__name__ in AnnotatedTypeNames:
        return cast(type[Any], Annotated)  # mypy complains about _SpecialForm
    return _typing_get_origin(tp) or getattr(tp, "__origin__", None)


# ----- get_args -----


def _generic_get_args(tp: type[Any]) -> tuple[Any, ...]:
    """Generic get args function.

    In python 3.9, `typing.Dict`, `typing.List`, ...
    do have an empty `__args__` by default (instead of the generic ~T
    for example). In order to still support `Dict` for example and consider
    it as `Dict[Any, Any]`, we retrieve the `_nparams` value that tells us
    how many parameters it needs.

    Args:
        tp: type to check.

    Returns:
        Tuple of all the args.
    """
    if hasattr(tp, "_nparams"):
        return (Any,) * tp._nparams  # type: ignore[no-any-return]
    # Special case for `tuple[()]`, which used to return ((),) with
    # `typing.Tuple in python 3.10- but now returns () for `tuple` and `Tuple`.
    try:
        if tp == tuple[()] or tp == tuple[()]:  # type: ignore[comparison-overlap]
            return ((),)
    # there is a TypeError when compiled with cython
    except TypeError:  # pragma: no cover
        pass
    return ()


def get_args(tp: type[Any]) -> tuple[Any, ...]:
    """Get type arguments with all substitutions performed.

    For unions, basic simplifications used by Union constructor are performed.
    Examples::
        get_args(Dict[str, int]) == (str, int)
        get_args(int) == ()
        get_args(Union[int, Union[T, int], str][int]) == (int, str)
        get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
        get_args(Callable[[], T][int]) == ([], int)

    Args:
        tp: the type to check.

    Returns:
        Tuple of all the args.
    """
    if type(tp).__name__ in AnnotatedTypeNames:
        return tp.__args__ + tp.__metadata__  # type: ignore[no-any-return]
    # the fallback is needed for the same reasons as `get_origin` (see above)
    return (
        _typing_get_args(tp)
        or getattr(tp, "__args__", ())
        or _generic_get_args(tp)
    )


def is_optional(tp: type[Any]) -> bool:
    """Checks whether a given annotation is typing.Optional.

    Args:
        tp: the type to check.

    Returns:
        boolean indicating if the type is typing.Optional.
    """
    return is_union(get_origin(tp)) and type(None) in get_args(tp)
