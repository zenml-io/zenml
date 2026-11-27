#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Generated filter cases and their independent reference semantics."""

from dataclasses import dataclass
from typing import List, Literal, Optional, Sequence, Union

from hypothesis import strategies as st

ColumnName = Literal["name", "number"]
LogicalOperator = Literal["and", "or"]
Scalar = Union[str, int]


@dataclass(frozen=True)
class RowValues:
    """Values stored in one generated database row."""

    id: int
    name: Optional[str]
    number: Optional[int]


@dataclass(frozen=True)
class FilterSpec:
    """A product-independent description of one generated predicate."""

    column: ColumnName
    operation: str
    value: Optional[Union[Scalar, Sequence[str]]] = None


@dataclass(frozen=True)
class FilterCase:
    """Rows, predicates, and logical operator for one property example."""

    rows: Sequence[RowValues]
    filters: Sequence[FilterSpec]
    logical_operator: LogicalOperator


# Include uppercase/lowercase, digits, spaces, colons, quotes, and non-ASCII
# while keeping `%` and `_` out of generated LIKE values (tested explicitly in
# test_filters.py because StrFilter currently passes raw patterns to LIKE).
PORTABLE_TEXT = st.text(
    alphabet="abcXYZ012- :'\"ü",
    min_size=0,
    max_size=16,
)
PORTABLE_NUMBER = st.integers(min_value=-10, max_value=10)


@st.composite
def _string_filter(draw: st.DrawFn) -> FilterSpec:
    operation = draw(
        st.sampled_from(
            [
                "equals",
                "notequals",
                "contains",
                "notcontains",
                "startswith",
                "endswith",
                "oneof",
                "notoneof",
                "isnull",
                "isnotnull",
            ]
        )
    )
    value: Optional[Union[Scalar, Sequence[str]]]
    if operation in {"isnull", "isnotnull"}:
        value = None
    elif operation in {"oneof", "notoneof"}:
        value = draw(st.lists(PORTABLE_TEXT, min_size=0, max_size=4))
    else:
        value = draw(PORTABLE_TEXT)
    return FilterSpec(column="name", operation=operation, value=value)


@st.composite
def _numeric_filter(draw: st.DrawFn) -> FilterSpec:
    operation = draw(
        st.sampled_from(
            [
                "equals",
                "notequals",
                "gt",
                "gte",
                "lt",
                "lte",
                "isnull",
                "isnotnull",
            ]
        )
    )
    value = (
        None if operation in {"isnull", "isnotnull"} else draw(PORTABLE_NUMBER)
    )
    return FilterSpec(column="number", operation=operation, value=value)


@st.composite
def filter_cases(draw: st.DrawFn) -> FilterCase:
    """Generate rows and valid filters covering string and integer columns."""
    raw_rows = draw(
        st.lists(
            st.tuples(
                st.one_of(st.none(), PORTABLE_TEXT),
                st.one_of(st.none(), PORTABLE_NUMBER),
            ),
            min_size=1,
            max_size=8,
        )
    )
    rows = [
        RowValues(id=index + 1, name=name, number=number)
        for index, (name, number) in enumerate(raw_rows)
    ]
    filters = draw(
        st.lists(
            st.one_of(_string_filter(), _numeric_filter()),
            min_size=1,
            max_size=3,
        )
    )
    return FilterCase(
        rows=rows,
        filters=filters,
        logical_operator=draw(st.sampled_from(["and", "or"])),
    )


MALFORMED_MEMBERSHIP_VALUES = st.sampled_from(
    [
        "",
        "not-json",
        "null",
        "42",
        '"value"',
        "{}",
        "[",
        '["value"',
    ]
)


def _normalize_text(value: str, *, case_insensitive: bool) -> str:
    """Normalize a string according to the active database collation."""
    return value.casefold() if case_insensitive else value


def _matches(
    row: RowValues, predicate: FilterSpec, *, backend: str = "sqlite"
) -> bool:
    """Evaluate one predicate using SQL NULL and backend collation semantics."""
    actual = row.name if predicate.column == "name" else row.number
    operation = predicate.operation
    if operation == "isnull":
        return actual is None
    if operation == "isnotnull":
        return actual is not None
    # Per zenml-io/zenml#5426, empty `oneof:[]` and `notoneof:[]` compile to
    # `true()` and match every row including NULLs.
    if operation in {"oneof", "notoneof"}:
        assert isinstance(predicate.value, list)
        if not predicate.value:
            return True
        if actual is None:
            return False
        assert isinstance(actual, str)
        ci = backend == "mysql"
        norm_actual = _normalize_text(actual, case_insensitive=ci)
        norm_values = [
            _normalize_text(item, case_insensitive=ci)
            for item in predicate.value
        ]
        return (
            norm_actual in norm_values
            if operation == "oneof"
            else norm_actual not in norm_values
        )
    if actual is None:
        return False
    if predicate.column == "name":
        assert isinstance(actual, str)
        assert isinstance(predicate.value, str)
        # SQLite `LIKE` is ASCII case-insensitive while `=` is binary; MySQL
        # 8.0 default `utf8mb4_0900_ai_ci` is case-insensitive for both.
        if operation in {"equals", "notequals"}:
            ci = backend == "mysql"
            left = _normalize_text(actual, case_insensitive=ci)
            right = _normalize_text(predicate.value, case_insensitive=ci)
            return left == right if operation == "equals" else left != right
        # `contains`, `notcontains`, `startswith`, `endswith` compile to LIKE.
        left = (
            actual.casefold()
            if backend == "mysql"
            else actual.lower()
            if actual.isascii()
            else _sqlite_ascii_lower(actual)
        )
        right = (
            predicate.value.casefold()
            if backend == "mysql"
            else predicate.value.lower()
            if predicate.value.isascii()
            else _sqlite_ascii_lower(predicate.value)
        )
        if operation == "contains":
            return right in left
        if operation == "notcontains":
            return right not in left
        if operation == "startswith":
            return left.startswith(right)
        if operation == "endswith":
            return left.endswith(right)
        raise AssertionError(f"Unknown string oracle operation: {operation}")
    assert isinstance(actual, int)
    assert isinstance(predicate.value, int)
    if operation == "equals":
        return actual == predicate.value
    if operation == "notequals":
        return actual != predicate.value
    if operation == "gt":
        return actual > predicate.value
    if operation == "gte":
        return actual >= predicate.value
    if operation == "lt":
        return actual < predicate.value
    if operation == "lte":
        return actual <= predicate.value
    raise AssertionError(f"Unknown numeric oracle operation: {operation}")


def _sqlite_ascii_lower(value: str) -> str:
    """Model SQLite's default LIKE folding (ASCII A-Z only, not Unicode)."""
    return "".join(ch.lower() if "A" <= ch <= "Z" else ch for ch in value)


def expected_ids(case: FilterCase, *, backend: str = "sqlite") -> List[int]:
    """Calculate matching IDs without using ZenML or SQLAlchemy."""
    combine = all if case.logical_operator == "and" else any
    return [
        row.id
        for row in case.rows
        if combine(
            _matches(row, predicate, backend=backend)
            for predicate in case.filters
        )
    ]
