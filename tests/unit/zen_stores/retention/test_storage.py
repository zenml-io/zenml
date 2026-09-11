# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Archive URI to artifact store flavor selection."""

import pytest

from zenml.zen_stores.retention.storage import _flavor_for


@pytest.mark.parametrize(
    ("uri", "flavor"),
    [
        ("s3://bucket/archive", "s3"),
        ("gs://bucket/archive", "gcp"),
        ("az://container/archive", "azure"),
        ("abfs://container/archive", "azure"),
        ("/var/lib/zenml/archive", "local"),
    ],
)
def test_archive_uri_selects_the_flavor_owning_its_scheme(
    uri: str, flavor: str
) -> None:
    """Production schemes resolve without credentials or network access."""
    assert _flavor_for(uri).name == flavor


def test_archive_uri_with_unknown_scheme_is_rejected() -> None:
    """A scheme no installed flavor supports fails instead of writing locally."""
    with pytest.raises(ValueError, match="ftp://"):
        _flavor_for("ftp://host/archive")
