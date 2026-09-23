# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Retained summaries preserve metadata-based response compatibility."""

import pytest


@pytest.mark.parametrize(
    "fixture_name,fields",
    [
        (
            "sample_snapshot_response_model",
            [
                "run_name_template",
                "client_version",
                "server_version",
                "pipeline_version_hash",
                "code_path",
                "template_id",
                "source_snapshot_id",
            ],
        ),
        ("sample_pipeline_run", ["start_time", "end_time", "run_metadata"]),
        (
            "sample_step_run",
            [
                "pipeline_run_id",
                "snapshot_id",
                "original_step_run_id",
                "parent_step_ids",
                "run_metadata",
            ],
        ),
    ],
)
def test_pre_archive_response_payload_still_supports_retained_properties(
    request, fixture_name, fields
):
    """Older responses without a summary retain their existing field values."""
    model = request.getfixturevalue(fixture_name)
    payload = model.model_dump()
    payload["body"].pop("summary", None)
    payload["body"].pop("archive", None)
    payload["body"].pop("archive_bundle_id", None)
    legacy = type(model).model_validate(payload)
    expected = legacy.get_metadata().model_dump()
    for field in fields:
        assert getattr(legacy, field) == expected[field]
    assert legacy.get_metadata().model_dump() == expected
