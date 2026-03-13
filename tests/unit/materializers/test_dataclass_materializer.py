from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

import pytest

from tests.unit.test_general import _test_materializer
from zenml.materializers.dataclass_materializer import DataclassMaterializer


@dataclass
class Address:
    """Address dataclass."""

    street: str
    zip_code: int


@dataclass
class User:
    """User dataclass."""

    name: str
    address: Address
    tags: Tuple[str, str]
    scores: Dict[str, int]
    nickname: Optional[str] = None


@dataclass
class UnserializableUser:
    """Dataclass with unserializable field types."""

    callback: Callable[[int], int]


def test_dataclass_materializer() -> None:
    """Tests the dataclass materializer."""
    user = User(
        name="zenml",
        address=Address(street="Main Street", zip_code=12345),
        tags=("core", "json"),
        scores={"quality": 10},
    )

    result = _test_materializer(
        step_output_type=User,
        materializer_class=DataclassMaterializer,
        step_output=user,
        expected_metadata_size=2,
        assert_visualization_exists=True,
    )

    assert result == user


def test_dataclass_materializer_rejects_non_dataclasses() -> None:
    """Tests that the dataclass materializer rejects non-dataclass types."""
    materializer = DataclassMaterializer(uri="")

    with pytest.raises(TypeError):
        materializer.validate_save_type_compatibility(dict)


def test_dataclass_materializer_rejects_non_json_serializable_types() -> None:
    """Tests that unserializable dataclass field types are rejected."""
    assert DataclassMaterializer.can_save_type(UnserializableUser) is False
