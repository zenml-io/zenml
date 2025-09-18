"""Unit tests for artifact utils behavior in in-memory serving mode."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from zenml.artifacts.utils import _store_artifact_data_and_prepare_request
from zenml.enums import ArtifactSaveType


class _MinimalMaterializer:
    ASSOCIATED_ARTIFACT_TYPE = "data"

    def __init__(self, uri: str, artifact_store: Any) -> None:  # noqa: D401
        self.uri = uri

    def validate_save_type_compatibility(self, data_type: type) -> None:  # noqa: D401
        return None

    def compute_content_hash(self, data: Any):  # noqa: D401
        return None


def test_ephemeral_tag_added_in_memory(monkeypatch: pytest.MonkeyPatch):
    """Verify that ephemeral tag is added when in-memory mode is active."""

    # Force in-memory mode
    class _R:
        @staticmethod
        def should_use_in_memory():  # noqa: D401
            return True

        @staticmethod
        def put_in_memory_data(uri: str, data: Any) -> None:  # noqa: D401
            pass

    monkeypatch.setattr("zenml.deployers.serving.runtime", _R)

    # Stub client/stack/artifact_store
    fake_store = MagicMock(id="store-id")
    monkeypatch.setattr(
        "zenml.artifacts.utils.Client",
        lambda: MagicMock(
            active_stack=MagicMock(artifact_store=fake_store),
            active_project=MagicMock(id="proj"),
        ),
    )

    req = _store_artifact_data_and_prepare_request(
        data={"a": 1},
        name="test-artifact",
        uri="memory://x/y",
        materializer_class=_MinimalMaterializer,
        save_type=ArtifactSaveType.STEP_OUTPUT,
        version=None,
        artifact_type=None,
        tags=["foo"],
        store_metadata=False,
        store_visualizations=False,
        has_custom_name=True,
        metadata=None,
    )

    assert any(t == "ephemeral:in-memory" for t in (req.tags or []))
