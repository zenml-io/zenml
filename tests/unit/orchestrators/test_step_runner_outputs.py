"""Unit tests for StepRunner output artifact persistence behavior."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple, Type
from unittest.mock import MagicMock

import pytest

from zenml.enums import ArtifactType
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.orchestrators.step_runner import StepRunner


class _DummyMaterializer(BaseMaterializer):
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA
    ASSOCIATED_TYPES = (int,)

    def __init__(self, uri: str, artifact_store: Any) -> None:
        self.uri = uri

    def validate_save_type_compatibility(self, data_type: type) -> None:  # noqa: D401
        return None


def test_store_multiple_output_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure multiple outputs are persisted and mapped correctly.

    Args:
        monkeypatch: The monkeypatch object.
    """
    # Prepare a StepRunner with minimal dependencies
    dummy_step = MagicMock()
    dummy_step.config.outputs = {"out1": MagicMock(), "out2": MagicMock()}
    runner = StepRunner(step=dummy_step, stack=MagicMock())

    # Patch get_step_context to provide required properties/methods
    class _Ctx:
        class _PR:  # pipeline_run
            class _P:
                name = "pipe"

            pipeline = _P()

            class _Cfg:
                tags = []

            config = _Cfg()

        class _SR:  # step_run
            name = "step"

        pipeline_run = _PR()
        step_run = _SR()

        def get_output_metadata(self, name: str):  # noqa: D401
            return {}

        def get_output_tags(self, name: str):  # noqa: D401
            return []

    monkeypatch.setattr(
        "zenml.orchestrators.step_runner.get_step_context", lambda: _Ctx()
    )

    # Prepare inputs to _store_output_artifacts
    output_data = {"out1": 1, "out2": 2}
    output_materializers: Dict[str, Tuple[Type[_DummyMaterializer], ...]] = {
        "out1": (_DummyMaterializer,),
        "out2": (_DummyMaterializer,),
    }
    output_uris = {"out1": "memory://uri1", "out2": "memory://uri2"}
    output_annotations = {
        "out1": MagicMock(artifact_config=None),
        "out2": MagicMock(artifact_config=None),
    }

    # Patch artifact pre-store util to avoid I/O and return request objects
    requests_created: List[Any] = []

    def _fake_store(**kwargs: Any):  # noqa: D401
        requests_created.append(kwargs)
        return MagicMock()

    monkeypatch.setattr(
        "zenml.orchestrators.step_runner._store_artifact_data_and_prepare_request",
        lambda **kwargs: _fake_store(**kwargs),
    )

    # Patch batch_create_artifact_versions to return two distinct responses
    resp1 = MagicMock(id="a1")
    resp2 = MagicMock(id="a2")
    monkeypatch.setattr(
        "zenml.orchestrators.step_runner.Client",
        lambda: MagicMock(
            zen_store=MagicMock(
                batch_create_artifact_versions=lambda reqs: [resp1, resp2]
            )
        ),
    )

    result = runner._store_output_artifacts(
        output_data=output_data,
        output_materializers=output_materializers,
        output_artifact_uris=output_uris,
        output_annotations=output_annotations,
        artifact_metadata_enabled=False,
        artifact_visualization_enabled=False,
    )

    # Ensure both outputs are present and mapped correctly
    assert set(result.keys()) == {"out1", "out2"}
    assert result["out1"].id == "a1"
    assert result["out2"].id == "a2"
