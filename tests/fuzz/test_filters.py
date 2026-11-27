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
from typing import Dict, Generator, List, Union

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError
from sqlalchemy import Engine, delete
from sqlmodel import Session, select
from tests.fuzz.database import FilterRow, filter_database
from tests.fuzz.filter_strategies import (
    MALFORMED_MEMBERSHIP_VALUES,
    PORTABLE_TEXT,
    FilterCase,
    FilterSpec,
    expected_ids,
    filter_cases,
)

from zenml.enums import LogicalOperators
from zenml.models import PipelineRunFilter
from zenml.models.v2.base.filter import (
    BaseFilter,
    IntegerFilterOption,
    StringFilterOption,
)


class GeneratedFilter(BaseFilter):
    """Filter model matching the SQL oracle table."""

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


@given(case=filter_cases())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@pytest.mark.filterwarnings(r"ignore:Invoking and_\(\) without arguments")
@pytest.mark.filterwarnings(r"ignore:Invoking or_\(\) without arguments")
def test_generated_filters_match_independent_oracle(
    case: FilterCase, filter_engine: Engine
) -> None:
    """Compare real SQLModel results with the independent Python oracle."""
    backend = os.environ.get("ZENML_FUZZ_BACKEND", "sqlite")
    actual = _execute_case(filter_engine, case)
    expected = sorted(expected_ids(case, backend=backend))
    assert actual == expected, (
        f"query returned IDs {actual}, oracle expected {expected} "
        f"(backend={backend})"
    )


@given(value=MALFORMED_MEMBERSHIP_VALUES)
def test_malformed_membership_values_fail_during_parsing(value: str) -> None:
    """Malformed list syntax fails before a database query is built."""
    with pytest.raises((ValueError, ValidationError)):
        GeneratedFilter(name=f"oneof:{value}")


@given(
    key=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
        min_size=1,
        max_size=16,
    ),
    scalars=st.lists(
        st.one_of(st.integers(min_value=-100, max_value=100), PORTABLE_TEXT),
        min_size=0,
        max_size=4,
    ),
    tag_names=st.lists(PORTABLE_TEXT, min_size=0, max_size=3),
)
def test_real_pipeline_run_filter_parses_metadata_and_tags(
    key: str, scalars: List[Union[int, str]], tag_names: List[str]
) -> None:
    """Real PipelineRunFilter accepts numeric run_metadata lists and tags."""
    metadata_expr = f"{key}:oneof:{json.dumps(scalars)}"
    tag_expr = f"oneof:{json.dumps(tag_names)}"
    run_filter = PipelineRunFilter(
        run_metadata=metadata_expr,
        tags=tag_expr,
    )
    assert run_filter.run_metadata == metadata_expr
    assert run_filter.tags == tag_expr


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="StrFilter.contains passes raw '%'/'_' to SQL LIKE without escaping",
)
def test_like_wildcards_in_contains_are_treated_literally(
    filter_engine: Engine,
) -> None:
    """Canary documenting that ``contains:%`` currently acts as a LIKE wildcard."""
    rows = [
        FilterRow(id=1, name="100%_ready", number=1),
        FilterRow(id=2, name="plain_text", number=2),
    ]
    with Session(filter_engine) as session:
        session.exec(delete(FilterRow))
        session.add_all(rows)
        session.commit()
        query = GeneratedFilter(name="contains:%").apply_filter(
            select(FilterRow),
            table=FilterRow,  # type: ignore[type-var]
        )
        matched = sorted(row.id for row in session.exec(query).all())
    assert matched == [1]
