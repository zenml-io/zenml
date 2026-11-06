#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Unit tests for filtering by tags and run metadata in SqlZenStore."""

import json
import random
from typing import Dict, Iterator, List, Optional, Set
from uuid import UUID, uuid4

import pytest
from sqlalchemy.dialects import mysql
from sqlmodel import select

from zenml.enums import (
    LogicalOperators,
    MetadataResourceTypes,
    TaggableResourceTypes,
)
from zenml.models import PipelineRunFilter, ProjectFilter
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    TagResourceSchema,
    TagSchema,
)
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
)

RUN_TAGS = [
    ["red", "blue"],
    ["red"],
    ["blue", "light-blue"],
    ["dark-red", "green", "blue"],
    ["green"],
    ["red", "green", "blue", "light-blue"],
    [],
    [],
]
RUN_METADATA = [
    {"color": "red", "score": 0.9},
    {"color": "blue", "score": 0.2},
    {"color": "blue"},
    {"score": 0.5},
    {},
    {"color": "green", "score": 0.7},
    {"color": "red"},
    {},
]
TAG_EXPRESSIONS = [
    "red",
    "blue",
    "green",
    "missing",
    "contains:red",
    "startswith:light",
    "endswith:blue",
    "notequals:red",
    "notcontains:blue",
    'oneof:["green","dark-red"]',
    'notoneof:["red","blue"]',
    "oneof:[]",
    "notoneof:[]",
    "isnull:",
    "isnotnull:",
]
METADATA_EXPRESSIONS = [
    "color:red",
    "color:blue",
    "color:contains:e",
    "score:gte:0.5",
    "score:lt:0.8",
    "missing:value",
]


@pytest.fixture(scope="module")
def sql_store(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[SqlZenStore]:
    """Create a SQLite-backed SqlZenStore that no test of this module modifies."""
    db_dir = tmp_path_factory.mktemp("zenml-cfg")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("ZENML_CONFIG_PATH", str(db_dir))
        config = SqlZenStoreConfiguration(
            url=f"sqlite:///{db_dir / 'test.db'}"
        )
        yield SqlZenStore(config=config, skip_default_registrations=False)


@pytest.fixture(scope="module")
def tagged_runs(sql_store: SqlZenStore) -> UUID:
    """Create runs with overlapping tags and run metadata.

    Every tag is also linked to a non-run resource whose ID collides with an
    untagged run, which must not make that run match any tag filter.

    Returns:
        The project ID of the runs.
    """
    project_id = (
        sql_store.list_projects(project_filter_model=ProjectFilter())
        .items[0]
        .id
    )
    with Session(sql_store.engine) as session:
        tags = {
            name: TagSchema(name=name, color="grey")
            for name in sorted({t for run in RUN_TAGS for t in run})
        }
        session.add_all(tags.values())
        session.flush()
        run_ids = []
        for index, (tag_names, metadata) in enumerate(
            zip(RUN_TAGS, RUN_METADATA)
        ):
            run = PipelineRunSchema(
                id=uuid4(),
                project_id=project_id,
                name=f"run-{index}",
                status="completed",
                index=index,
                in_progress=False,
                enable_heartbeat=False,
            )
            session.add(run)
            run_ids.append(run.id)
            for name in tag_names:
                session.add(
                    TagResourceSchema(
                        tag_id=tags[name].id,
                        resource_id=run.id,
                        resource_type=TaggableResourceTypes.PIPELINE_RUN.value,
                    )
                )
            for key, value in metadata.items():
                run_metadata = RunMetadataSchema(
                    project_id=project_id,
                    key=key,
                    value=json.dumps(value),
                    type="str" if isinstance(value, str) else "float",
                )
                session.add(run_metadata)
                session.flush()
                session.add(
                    RunMetadataResourceSchema(
                        resource_id=run.id,
                        resource_type=MetadataResourceTypes.PIPELINE_RUN.value,
                        run_metadata_id=run_metadata.id,
                    )
                )
        for tag in tags.values():
            session.add(
                TagResourceSchema(
                    tag_id=tag.id,
                    resource_id=run_ids[-1],
                    resource_type=TaggableResourceTypes.ARTIFACT.value,
                )
            )
        session.commit()
    return project_id


def _list_run_names(
    store: SqlZenStore,
    project_id: UUID,
    tags: Optional[List[str]] = None,
    run_metadata: Optional[List[str]] = None,
    logical_operator: LogicalOperators = LogicalOperators.AND,
) -> Set[str]:
    filter_model = PipelineRunFilter(
        project=project_id,
        tags=tags,
        run_metadata=run_metadata,
        logical_operator=logical_operator,
        size=100,
    )
    with Session(store.engine) as session:
        page = store.filter_and_paginate(
            session=session,
            query=select(PipelineRunSchema),
            table=PipelineRunSchema,
            filter_model=filter_model,
            custom_schema_to_model_conversion=lambda run: run.name,
        )
    names = set(page.items)
    assert page.total == len(names)
    return names


def _expected_run_names(
    single_results: Dict[str, Set[str]],
    expressions: List[str],
    logical_operator: LogicalOperators,
) -> Set[str]:
    results = [single_results[expression] for expression in expressions]
    if logical_operator == LogicalOperators.AND:
        return set.intersection(*results)
    return set.union(*results)


@pytest.mark.parametrize(
    "logical_operator", [LogicalOperators.AND, LogicalOperators.OR]
)
def test_combined_tag_and_metadata_filters_match_single_filters(
    sql_store: SqlZenStore,
    tagged_runs: UUID,
    logical_operator: LogicalOperators,
) -> None:
    """Combining filters is equivalent to combining their results.

    The combinations cover both the separate and the aggregated subqueries
    generated for tags and run metadata, including empty `oneof` lists and
    duplicated expressions.
    """
    single_tag_results = {
        expression: _list_run_names(sql_store, tagged_runs, tags=[expression])
        for expression in TAG_EXPRESSIONS
    }
    single_metadata_results = {
        expression: _list_run_names(
            sql_store, tagged_runs, run_metadata=[expression]
        )
        for expression in METADATA_EXPRESSIONS
    }
    assert single_tag_results["red"] == {"run-0", "run-1", "run-5"}
    assert single_tag_results["isnull:"] == {"run-6", "run-7"}
    assert single_metadata_results["color:red"] == {"run-0", "run-6"}
    assert single_metadata_results["score:gte:0.5"] == {
        "run-0",
        "run-3",
        "run-5",
    }

    rng = random.Random(0)
    for _ in range(40):
        tags = rng.choices(TAG_EXPRESSIONS, k=rng.randint(1, 8))
        run_metadata = rng.choices(METADATA_EXPRESSIONS, k=rng.randint(0, 5))
        expected = _expected_run_names(
            {**single_tag_results, **single_metadata_results},
            tags + run_metadata,
            logical_operator,
        )
        assert (
            _list_run_names(
                sql_store,
                tagged_runs,
                tags=tags,
                run_metadata=run_metadata or None,
                logical_operator=logical_operator,
            )
            == expected
        ), (tags, run_metadata)


@pytest.mark.parametrize(
    "tags,run_metadata,expected",
    [
        (["red", "blue", "contains:light"], None, {"run-5"}),
        (["red", "blue", "oneof:[]", "contains:green"], None, {"run-5"}),
        (
            ["red", "notoneof:[]", "contains:blue", "contains:light"],
            None,
            {"run-5"},
        ),
        (None, ["color:red", "score:gte:0.5"], {"run-0"}),
        (["blue"], ["color:contains:e", "score:lt:0.8"], {"run-5"}),
    ],
)
def test_aggregated_filters(
    sql_store: SqlZenStore,
    tagged_runs: UUID,
    tags: Optional[List[str]],
    run_metadata: Optional[List[str]],
    expected: Set[str],
) -> None:
    """Predicates checked by an aggregated subquery all have to match."""
    assert (
        _list_run_names(
            sql_store, tagged_runs, tags=tags, run_metadata=run_metadata
        )
        == expected
    )


def _count_exists_subqueries(filter_model: PipelineRunFilter) -> int:
    filter_model.project = uuid4()
    query = filter_model.apply_filter(
        select(PipelineRunSchema.id), PipelineRunSchema
    )
    return str(query.compile(dialect=mysql.dialect())).count("EXISTS")


@pytest.mark.parametrize("count", [3, 16, 64])
def test_and_filters_bound_subqueries_that_are_expensive_to_plan(
    count: int,
) -> None:
    """Only exact tag names may add any number of separate subqueries."""
    exact_tags = [f"tag-{i}" for i in range(count)]
    other_tags = [f"contains:tag-{i}" for i in range(count)]
    run_metadata = [f"key-{i}:value" for i in range(count)]

    assert _count_exists_subqueries(PipelineRunFilter(tags=other_tags)) == 3
    assert (
        _count_exists_subqueries(PipelineRunFilter(tags=["tag", *other_tags]))
        == 3
    )
    assert (
        _count_exists_subqueries(PipelineRunFilter(run_metadata=run_metadata))
        == 1
    )
    assert (
        _count_exists_subqueries(
            PipelineRunFilter(
                tags=exact_tags + other_tags, run_metadata=run_metadata
            )
        )
        == count + 2
    )
    assert (
        _count_exists_subqueries(
            PipelineRunFilter(
                tags=exact_tags + other_tags,
                run_metadata=run_metadata,
                logical_operator=LogicalOperators.OR,
            )
        )
        == 3 * count
    )


def test_duplicate_filter_expressions_are_ignored() -> None:
    """Repeating an expression adds no subqueries."""
    assert _count_exists_subqueries(PipelineRunFilter(tags=["red"] * 16)) == 1
    assert (
        _count_exists_subqueries(
            PipelineRunFilter(run_metadata=["color:red"] * 16)
        )
        == 1
    )
