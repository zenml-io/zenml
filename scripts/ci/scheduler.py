"""Batch pytest node IDs using longest-processing-time-first scheduling."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

DEFAULT_UNIT_TEST_DURATION_SECONDS = 0.5
DEFAULT_INTEGRATION_TEST_DURATION_SECONDS = 5.0

_DURATION_LINE_PATTERN = re.compile(
    r"^(?P<nodeid>.+?)[\s,|]+(?P<duration>\d+(?:\.\d+)?)$"
)


@dataclass(frozen=True)
class ScheduledBatch:
    """A batch of tests with its estimated duration."""

    node_ids: tuple[str, ...]
    duration_seconds: float


def read_durations_file(path: Path) -> dict[str, float]:
    """Read a pytest-split durations file into a node ID to duration map."""
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}

    parsed = _parse_json_durations(text)
    if parsed is not None:
        return parsed

    durations: dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = _DURATION_LINE_PATTERN.match(line)
        if match is None:
            continue

        node_id = match.group("nodeid").strip()
        duration_seconds = float(match.group("duration"))
        durations[node_id] = duration_seconds

    return durations


def schedule_batches(
    node_ids: Sequence[str],
    max_batches: int,
    *,
    durations: Mapping[str, float] | None = None,
    default_duration_seconds: float = DEFAULT_UNIT_TEST_DURATION_SECONDS,
    group_by_scope: bool = False,
    max_group_size: int | None = None,
) -> list[ScheduledBatch]:
    """Group node IDs into balanced batches with an LPT heuristic.

    When `group_by_scope=True`, batching happens by pytest-xdist loadscope
    boundaries rather than by individual node IDs. This aligns the estimated
    work with how unit tests are actually distributed to workers when we use
    ``--dist loadscope``.
    """
    if max_batches <= 0:
        raise ValueError("max_batches must be greater than zero")

    if not node_ids:
        return []

    durations = durations or {}
    estimated_durations = _estimate_node_durations(
        node_ids=node_ids,
        durations=durations,
        default_duration_seconds=default_duration_seconds,
    )
    if max_group_size is not None and max_group_size <= 0:
        raise ValueError("max_group_size must be greater than zero")

    if group_by_scope:
        grouped_node_ids = _chunk_grouped_node_ids(
            grouped_node_ids=list(_group_node_ids_by_scope(node_ids).values()),
            max_group_size=max_group_size,
        )
    else:
        grouped_node_ids = [[node_id] for node_id in node_ids]

    batch_count = min(len(grouped_node_ids), max_batches)

    weighted_groups = sorted(
        (
            (
                index,
                scope_node_ids,
                sum(estimated_durations[node_id] for node_id in scope_node_ids),
            )
            for index, scope_node_ids in enumerate(grouped_node_ids)
        ),
        key=lambda item: (-item[2], item[0]),
    )

    batches: list[list[str]] = [[] for _ in range(batch_count)]
    batch_durations = [0.0] * batch_count

    for _, scope_node_ids, duration_seconds in weighted_groups:
        batch_index = min(
            range(batch_count),
            key=lambda index: (
                batch_durations[index],
                len(batches[index]),
                index,
            ),
        )
        batches[batch_index].extend(scope_node_ids)
        batch_durations[batch_index] += duration_seconds

    return [
        ScheduledBatch(
            node_ids=tuple(batch),
            duration_seconds=batch_durations[index],
        )
        for index, batch in enumerate(batches)
        if batch
    ]


def _parse_json_durations(text: str) -> dict[str, float] | None:
    """Parse JSON duration data when pytest-split stores structured content."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if isinstance(data, dict):
        if all(_looks_like_number(value) for value in data.values()):
            return {str(key): float(value) for key, value in data.items()}

        for key in ("durations", "tests"):
            nested = data.get(key)
            if isinstance(nested, dict) and all(
                _looks_like_number(value) for value in nested.values()
            ):
                return {str(name): float(value) for name, value in nested.items()}

    return None


def _looks_like_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _estimate_node_durations(
    *,
    node_ids: Sequence[str],
    durations: Mapping[str, float],
    default_duration_seconds: float,
) -> dict[str, float]:
    """Estimate durations using node, scope, and file-level history."""
    scope_buckets: dict[str, list[float]] = defaultdict(list)
    file_buckets: dict[str, list[float]] = defaultdict(list)
    for node_id, duration in durations.items():
        scope_buckets[_scope_key(node_id)].append(duration)
        file_buckets[_file_key(node_id)].append(duration)

    scope_defaults = {
        key: sum(values) / len(values) for key, values in scope_buckets.items()
    }
    file_defaults = {
        key: sum(values) / len(values) for key, values in file_buckets.items()
    }

    estimates: dict[str, float] = {}
    for node_id in node_ids:
        if node_id in durations:
            estimates[node_id] = durations[node_id]
            continue

        scope_key = _scope_key(node_id)
        file_key = _file_key(node_id)
        estimates[node_id] = scope_defaults.get(
            scope_key,
            file_defaults.get(file_key, default_duration_seconds),
        )

    return estimates


def _group_node_ids_by_scope(node_ids: Sequence[str]) -> dict[str, list[str]]:
    """Group node IDs by the pytest-xdist loadscope boundary."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for node_id in node_ids:
        grouped[_scope_key(node_id)].append(node_id)
    return grouped


def _chunk_grouped_node_ids(
    *,
    grouped_node_ids: list[list[str]],
    max_group_size: int | None,
) -> list[list[str]]:
    """Split oversized scope groups into smaller deterministic chunks."""
    if max_group_size is None:
        return grouped_node_ids

    chunked_groups: list[list[str]] = []
    for scope_node_ids in grouped_node_ids:
        for start in range(0, len(scope_node_ids), max_group_size):
            chunked_groups.append(scope_node_ids[start : start + max_group_size])
    return chunked_groups


def _scope_key(node_id: str) -> str:
    """Return the loadscope grouping key for a pytest node ID."""
    parts = node_id.split("::")
    if len(parts) >= 3:
        return "::".join(parts[:2])
    return parts[0]


def _file_key(node_id: str) -> str:
    """Return the test file path portion of a pytest node ID."""
    return node_id.split("::", 1)[0]
