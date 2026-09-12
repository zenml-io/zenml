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
"""Generated checks for ZenML filter parsing and SQL result semantics."""

import json
import os
from typing import Dict, Generator, List, Sequence, Union

import pytest
from hypothesis import HealthCheck, given, settings
from pydantic import ValidationError
from sqlalchemy import Engine, delete
from sqlmodel import Session, select
from tests.fuzz.database import FilterRow, filter_database
from tests.fuzz.filter_strategies import (
    MALFORMED_MEMBERSHIP_VALUES,
    FilterCase,
    FilterSpec,
    expected_ids,
    filter_cases,
)

from zenml.enums import LogicalOperators
from zenml.models.v2.base.filter import (
    BaseFilter,
    IntegerFilterOption,
    StringFilterOption,
)


class GeneratedFilter(BaseFilter):
    """Filter model matching the deliberately small SQL test table."""

    name: StringFilterOption = None
    number: IntegerFilterOption = None


@pytest.fixture(scope="module")
def filter_engine() -> Generator[Engine, None, None]:
    """Provide one run-owned engine whose rows are reset per example."""
    with filter_database() as engine:
        yield engine


def _encoded_filter(predicate: FilterSpec) -> str:
    if predicate.operation in {"isnull", "isnotnull"}:
        return f"{predicate.operation}:"
    if predicate.operation in {"oneof", "notoneof"}:
        return f"{predicate.operation}:{json.dumps(predicate.value)}"
    return f"{predicate.operation}:{predicate.value}"


def _filter_model(case: FilterCase) -> GeneratedFilter:
    values: Dict[str, Union[str, List[str]]] = {}
    for predicate in case.filters:
        encoded = _encoded_filter(predicate)
        existing = values.get(predicate.column)
        if existing is None:
            values[predicate.column] = encoded
        elif isinstance(existing, list):
            existing.append(encoded)
        else:
            values[predicate.column] = [existing, encoded]
    return GeneratedFilter(
        **values,
        logical_operator=LogicalOperators(case.logical_operator),
    )


def _execute_case(engine: Engine, case: FilterCase) -> List[int]:
    with Session(engine) as session:
        session.exec(delete(FilterRow))
        session.add_all(
            [
                FilterRow(id=row.id, name=row.name, number=row.number)
                for row in case.rows
            ]
        )
        session.commit()
        query = _filter_model(case).apply_filter(
            select(FilterRow),
            table=FilterRow,  # type: ignore[type-var]
        )
        return sorted(row.id for row in session.exec(query).all())


def _assert_matching_ids(
    actual: Sequence[int], expected: Sequence[int]
) -> None:
    assert list(actual) == list(expected), (
        f"query returned IDs {list(actual)}, oracle expected {list(expected)}"
    )


def test_result_oracle_rejects_an_injected_mismatch() -> None:
    """Prove that successful execution with an extra ID cannot pass."""
    with pytest.raises(AssertionError, match="oracle expected"):
        _assert_matching_ids([1, 2], [1])


@given(case=filter_cases())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.filterwarnings(r"ignore:Invoking and_\(\) without arguments")
@pytest.mark.filterwarnings(r"ignore:Invoking or_\(\) without arguments")
def test_generated_filters_match_independent_oracle(
    case: FilterCase, filter_engine: Engine
) -> None:
    """Compare real SQLModel results with the independent Python predicate."""
    _assert_matching_ids(
        _execute_case(filter_engine, case), sorted(expected_ids(case))
    )


@given(value=MALFORMED_MEMBERSHIP_VALUES)
def test_malformed_membership_values_fail_during_parsing(value: str) -> None:
    """Malformed list syntax fails before a database query is built."""
    with pytest.raises((ValueError, ValidationError)):
        GeneratedFilter(name=f"oneof:{value}")


def test_dialect_sensitive_string_probes_are_explicit(
    filter_engine: Engine,
) -> None:
    """Exercise Unicode, long, wildcard, numeric, and trailing-space values."""
    long_value = "a" * 256
    rows = [
        FilterRow(id=1, name="Gr\u00fc\u00dfe", number=0),
        FilterRow(id=2, name="100%_ready", number=-1),
        FilterRow(id=3, name="123", number=1),
        FilterRow(id=4, name="trail", number=None),
        FilterRow(id=5, name="trail ", number=2),
        FilterRow(id=6, name=long_value, number=3),
    ]
    with Session(filter_engine) as session:
        session.exec(delete(FilterRow))
        session.add_all(rows)
        session.commit()

        for value, expected in [
            ("Gr\u00fc\u00dfe", [1]),
            ("100%_ready", [2]),
            ("123", [3]),
            (long_value, [6]),
        ]:
            query = GeneratedFilter(name=f"equals:{value}").apply_filter(
                select(FilterRow),
                table=FilterRow,  # type: ignore[type-var]
            )
            assert (
                sorted(row.id for row in session.exec(query).all()) == expected
            )

        trailing_query = GeneratedFilter(name="equals:trail ").apply_filter(
            select(FilterRow),
            table=FilterRow,  # type: ignore[type-var]
        )
        trailing_ids = sorted(
            row.id for row in session.exec(trailing_query).all()
        )
        wildcard_query = GeneratedFilter(name="contains:%").apply_filter(
            select(FilterRow),
            table=FilterRow,  # type: ignore[type-var]
        )
        wildcard_ids = sorted(
            row.id for row in session.exec(wildcard_query).all()
        )

    assert wildcard_ids == [1, 2, 3, 4, 5, 6]
    if os.environ.get("ZENML_FUZZ_BACKEND", "sqlite") == "mysql":
        assert trailing_ids == [4, 5]
    else:
        assert trailing_ids == [5]
