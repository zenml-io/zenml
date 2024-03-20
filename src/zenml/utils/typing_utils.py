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

import sys
import typing
from typing import (
    Annotated,
    Any,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)
from typing import get_args as _typing_get_args
from typing import get_origin as _typing_get_origin

NoneType = None.__class__

NONE_TYPES: Tuple[Any, Any, Any] = (None, NoneType, Literal[None])
LITERAL_TYPES: Set[Any] = {Literal}

# Annotated[...] is implemented by returning an instance of one of these
# classes, depending on python/typing_extensions version.
AnnotatedTypeNames = {"AnnotatedMeta", "_AnnotatedAlias"}

if hasattr(typing, "Literal"):
    LITERAL_TYPES.add(typing.Literal)

# ----- is_none_type -----

if sys.version_info[:2] == (3, 8):

    def is_none_type(type_: Any) -> bool:
        for none_type in NONE_TYPES:
            if type_ is none_type:
                return True
        # With python 3.8, specifically 3.8.10, Literal "is" checks are very
        # flakey can change on very subtle changes like use of types in other
        # modules, hopefully this check avoids that issue.
        if is_literal_type(type_):  # pragma: no cover
            return all_literal_values(type_) == (None,)
        return False
else:

    def is_none_type(type_: Any) -> bool:
        return type_ in NONE_TYPES

# ----- is_union -----

if sys.version_info < (3, 10):

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union


else:
    import types

    def is_union(tp: Optional[Type[Any]]) -> bool:
        return tp is Union or tp is types.UnionType  # noqa: E721


# ----- get_origin -----


def get_origin(tp: Type[Any]) -> Optional[Type[Any]]:
    """
    We can't directly use `typing.get_origin` since we need a fallback to
    support custom generic classes like `ConstrainedList`
    It should be useless once https://github.com/cython/cython/issues/3537 is
    solved and https://github.com/pydantic/pydantic/pull/1753 is merged.
    """
    if type(tp).__name__ in AnnotatedTypeNames:
        return cast(Type[Any], Annotated)  # mypy complains about _SpecialForm
    return _typing_get_origin(tp) or getattr(tp, "__origin__", None)


# ----- get_args -----


def _generic_get_args(tp: Type[Any]) -> Tuple[Any, ...]:
    """
    In python 3.9, `typing.Dict`, `typing.List`, ...
    do have an empty `__args__` by default (instead of the generic ~T
    for example). In order to still support `Dict` for example and consider
    it as `Dict[Any, Any]`, we retrieve the `_nparams` value that tells us
    how many parameters it needs.
    """
    if hasattr(tp, "_nparams"):
        return (Any,) * tp._nparams
    # Special case for `tuple[()]`, which used to return ((),) with
    # `typing.Tuple in python 3.10- but now returns () for `tuple` and `Tuple`.
    # This will probably be clarified in pydantic v2
    try:
        if tp == Tuple[()] or sys.version_info >= (3, 9) and tp == tuple[()]:  # type: ignore[misc]
            return ((),)
    # there is a TypeError when compiled with cython
    except TypeError:  # pragma: no cover
        pass
    return ()


def get_args(tp: Type[Any]) -> Tuple[Any, ...]:
    """Get type arguments with all substitutions performed.

    For unions, basic simplifications used by Union constructor are performed.
    Examples::
        get_args(Dict[str, int]) == (str, int)
        get_args(int) == ()
        get_args(Union[int, Union[T, int], str][int]) == (int, str)
        get_args(Union[int, Tuple[T, int]][str]) == (int, Tuple[str, int])
        get_args(Callable[[], T][int]) == ([], int)
    """
    if type(tp).__name__ in AnnotatedTypeNames:
        return tp.__args__ + tp.__metadata__
    # the fallback is needed for the same reasons as `get_origin` (see above)
    return (
        _typing_get_args(tp)
        or getattr(tp, "__args__", ())
        or _generic_get_args(tp)
    )


# ----- literal -----


def is_literal_type(type_: Type[Any]) -> bool:
    return Literal is not None and get_origin(type_) in LITERAL_TYPES


def literal_values(type_: Type[Any]) -> Tuple[Any, ...]:
    return get_args(type_)


def all_literal_values(type_: Type[Any]) -> Tuple[Any, ...]:
    """
    This method is used to retrieve all Literal values as Literal can be
    used recursively (see https://www.python.org/dev/peps/pep-0586)
    e.g. `Literal[Literal[Literal[1, 2, 3], "foo"], 5, None]`
    """
    if not is_literal_type(type_):
        return (type_,)

    values = literal_values(type_)
    return tuple(x for value in values for x in all_literal_values(value))
