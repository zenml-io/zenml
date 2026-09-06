"""Run pages preserve filtering and response content when IDs are fetched first."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from zenml.client import Client
from zenml.enums import TaggableResourceTypes
from zenml.models import PipelineRunFilter
from zenml.zen_stores.schemas import (
    PipelineRunSchema,
    PipelineSchema,
    TagResourceSchema,
    TagSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.fixture
def populated_store(clean_client: Client) -> SqlZenStore:
    """Seed tied ordering, overlapping tags and both status values."""
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    project_id = clean_client.active_project.id
    with Session(store.engine) as session:
        pipeline = PipelineSchema(
            name="pagination", project_id=project_id, run_count=9
        )
        tags = [TagSchema(name=name, color="blue") for name in ("a", "b")]
        session.add_all([pipeline, *tags])
        session.flush()
        for i in range(9):
            run = PipelineRunSchema(
                id=UUID(int=i + 1),
                name=f"page-{i}",
                index=i + 1,
                project_id=project_id,
                user_id=clean_client.active_user.id,
                pipeline_id=pipeline.id,
                in_progress=False,
                enable_heartbeat=False,
                pipeline_configuration='{"name": "pagination"}',
                created=datetime(2026, 1, 1),
                start_time=datetime(2026, 1, 1),
                status="completed" if i % 2 else "failed",
            )
            session.add(run)
            session.flush()
            for tag in tags[: 1 + i % 2]:
                session.add(
                    TagResourceSchema(
                        tag_id=tag.id,
                        resource_id=run.id,
                        resource_type=TaggableResourceTypes.PIPELINE_RUN.value,
                    )
                )
        session.commit()
    return store


@pytest.mark.parametrize(
    "sort_by, criteria, hydrate",
    [
        # Sorts on run columns take the ID-first path.
        *(
            (sort_by, criteria, hydrate)
            for sort_by in [
                "asc:created",
                "desc:created",
                "asc:id",
                "desc:index",
            ]
            for criteria in [
                {},
                {"status": "completed"},
                {"tags": ["a", "b"]},
                {
                    "status": "completed",
                    "name": "page-0",
                    "logical_operator": "or",
                },
            ]
            for hydrate in [False, True]
        ),
        # Sorts on related entities fall back to loading the page directly.
        ("asc:pipeline", {}, False),
        ("asc:user", {}, False),
        ("desc:tags", {"tags": ["a", "b"]}, False),
    ],
)
def test_pages_match_existing_query(
    populated_store: SqlZenStore,
    sort_by: str,
    criteria: dict[str, Any],
    hydrate: bool,
) -> None:
    """All projected fields, totals, resources and metadata retain parity."""
    store = populated_store
    first = store.list_runs(
        PipelineRunFilter(size=2, sort_by=sort_by, **criteria), hydrate=hydrate
    )
    seen: list[UUID] = []
    for page in range(1, first.total_pages + 1):
        filters = PipelineRunFilter(
            size=2, page=page, sort_by=sort_by, **criteria
        )
        actual = store.list_runs(filters, hydrate=hydrate)
        # The same query through the paginator without ID-first fetching.
        with Session(store.engine) as session:
            expected = store.filter_and_paginate(
                session,
                select(PipelineRunSchema),
                PipelineRunSchema,
                filters,
                hydrate=hydrate,
                apply_query_options_from_schema=True,
                query_options_kwargs={"include_full_metadata": False},
            )
        assert actual == expected
        seen.extend(row.id for row in actual.items)
    assert len(seen) == len(set(seen)) == first.total
    if not criteria and sort_by.endswith("created"):
        assert seen == sorted(seen, reverse=sort_by.startswith("desc"))


def test_authorization_is_applied_before_pagination(
    populated_store: SqlZenStore,
) -> None:
    """A small authorized set gets full pages, without leaking skipped rows."""
    filters = PipelineRunFilter(size=2, page=2, sort_by="asc:created")
    filters.configure_rbac(uuid4(), id={UUID(int=i) for i in (2, 4, 6, 8)})
    page = populated_store.list_runs(filters)
    assert page.total == 4
    assert [run.id for run in page.items] == [UUID(int=6), UUID(int=8)]


def test_empty_and_out_of_range_pages(populated_store: SqlZenStore) -> None:
    """An empty filter still has one page and invalid pages are refused."""
    page = populated_store.list_runs(PipelineRunFilter(name="missing"))
    assert page.total == 0 and page.total_pages == 1 and page.items == []
    with pytest.raises(ValueError, match="Invalid page"):
        populated_store.list_runs(PipelineRunFilter(size=2, page=6))
