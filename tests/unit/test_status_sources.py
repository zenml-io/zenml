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
"""Unit tests for `compose_status_source`."""

from zenml.enums import ExecutionStatus
from zenml.status_sources import (
    UNKNOWN_STATUS_SOURCE,
    compose_status_source,
    request_source_info,
)


def test_declared_slug_passthrough():
    """Tests that the declared slug is used as-is."""
    result = compose_status_source(
        declared="step_runner.success",
        requested=None,
        stored=ExecutionStatus.COMPLETED,
    )
    assert result == "step_runner.success"


def test_none_declared_falls_back_to_unknown():
    """Tests that a missing declared slug falls back to the unknown source."""
    result = compose_status_source(
        declared=None,
        requested=None,
        stored=ExecutionStatus.COMPLETED,
    )
    assert result == UNKNOWN_STATUS_SOURCE


def test_requested_segment_omitted_when_matching_stored():
    """Tests that no `requested` segment is added when the stored status matches."""
    result = compose_status_source(
        declared="step_runner.success",
        requested=ExecutionStatus.COMPLETED,
        stored=ExecutionStatus.COMPLETED,
    )
    assert result == "step_runner.success"


def test_requested_segment_present_when_differing_from_stored():
    """Tests that a `requested` segment is added when the stored status differs."""
    result = compose_status_source(
        declared="server.retry_superseded",
        requested=ExecutionStatus.FAILED,
        stored=ExecutionStatus.RETRYING,
    )
    assert result == "server.retry_superseded,requested:failed"


def test_channel_and_client_segments_from_context_var():
    """Tests that the channel and client version are read from the context var."""
    token = request_source_info.set(("python", "0.85.0"))
    try:
        result = compose_status_source(
            declared="step_runner.success",
            requested=None,
            stored=ExecutionStatus.COMPLETED,
        )
    finally:
        request_source_info.reset(token)

    assert result == "step_runner.success,channel:python,client:0.85.0"


def test_client_segment_omitted_when_version_is_none():
    """Tests that no `client` segment is added when the version is None."""
    token = request_source_info.set(("dashboard", None))
    try:
        result = compose_status_source(
            declared=None,
            requested=None,
            stored=ExecutionStatus.COMPLETED,
        )
    finally:
        request_source_info.reset(token)

    assert result == f"{UNKNOWN_STATUS_SOURCE},channel:dashboard"


def test_truncation_to_255_characters():
    """Tests that the composed result is truncated to 255 characters."""
    token = request_source_info.set(("python", "0.85.0"))
    try:
        result = compose_status_source(
            declared="x" * 300,
            requested=ExecutionStatus.FAILED,
            stored=ExecutionStatus.RETRYING,
        )
    finally:
        request_source_info.reset(token)

    assert len(result) == 255
    assert result == ("x" * 300)[:255]
