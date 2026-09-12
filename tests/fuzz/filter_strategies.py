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


PORTABLE_TEXT = st.text(alphabet="abcXYZ012_-", min_size=0, max_size=12)
PORTABLE_NUMBER = st.integers(min_value=-10, max_value=10)


@st.composite
def _string_filter(draw: st.DrawFn) -> FilterSpec:
    operation = draw(
        st.sampled_from(
            [
                "equals",
                "notequals",
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
    """Generate portable rows and valid filters for both SQL dialects."""
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
        '[["nested"]]',
        "[1]",
        "[true]",
        "[null]",
        "[{}]",
    ]
)


def _matches(row: RowValues, predicate: FilterSpec) -> bool:
    """Evaluate one predicate with explicit SQL NULL behavior."""
    actual = row.name if predicate.column == "name" else row.number
    operation = predicate.operation
    if operation == "isnull":
        return actual is None
    if operation == "isnotnull":
        return actual is not None
    if operation == "oneof":
        assert isinstance(predicate.value, list)
        return actual is not None and actual in predicate.value
    if operation == "notoneof":
        assert isinstance(predicate.value, list)
        if not predicate.value:
            return True
        return actual is not None and actual not in predicate.value
    if actual is None:
        return False
    if operation == "equals":
        return actual == predicate.value
    if operation == "notequals":
        return actual != predicate.value
    assert isinstance(actual, int)
    assert isinstance(predicate.value, int)
    if operation == "gt":
        return actual > predicate.value
    if operation == "gte":
        return actual >= predicate.value
    if operation == "lt":
        return actual < predicate.value
    if operation == "lte":
        return actual <= predicate.value
    raise AssertionError(f"Unknown oracle operation: {operation}")


def expected_ids(case: FilterCase) -> List[int]:
    """Calculate matching IDs without using ZenML or SQLAlchemy."""
    combine = all if case.logical_operator == "and" else any
    return [
        row.id
        for row in case.rows
        if combine(_matches(row, predicate) for predicate in case.filters)
    ]
