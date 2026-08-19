from zenml.cli.login import _resolve_workspace_id_from_device_metadata


def test_resolve_workspace_id_from_device_metadata_uses_current_key() -> None:
    workspace_id = _resolve_workspace_id_from_device_metadata(
        {"workspace_id": "abc123"}
    )

    assert workspace_id == "abc123"


def test_resolve_workspace_id_from_device_metadata_falls_back_to_legacy_key() -> (
    None
):
    workspace_id = _resolve_workspace_id_from_device_metadata(
        {"tenant_id": "legacy123"}
    )

    assert workspace_id == "legacy123"


def test_resolve_workspace_id_from_device_metadata_prefers_current_key() -> (
    None
):
    workspace_id = _resolve_workspace_id_from_device_metadata(
        {"workspace_id": "abc123", "tenant_id": "legacy123"}
    )

    assert workspace_id == "abc123"


def test_resolve_workspace_id_from_device_metadata_returns_none_when_missing() -> (
    None
):
    workspace_id = _resolve_workspace_id_from_device_metadata(
        {"some_other_key": "value"}
    )

    assert workspace_id is None


def test_resolve_workspace_id_from_device_metadata_handles_empty_dict() -> (
    None
):
    workspace_id = _resolve_workspace_id_from_device_metadata({})

    assert workspace_id is None


def test_resolve_workspace_id_from_device_metadata_handles_none() -> None:
    workspace_id = _resolve_workspace_id_from_device_metadata(None)

    assert workspace_id is None
