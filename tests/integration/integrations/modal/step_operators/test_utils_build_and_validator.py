import pytest

# Skip this entire module if the optional dependency isn't available, because
# the module under test imports `modal` at import time.
pytest.importorskip("modal")

from zenml.integrations.modal.utils import (
    build_modal_image,
    get_modal_stack_validator,
)
from zenml.stack.stack_validator import StackValidator


class StackStubNoRegistry:
    """Stack stub with no container registry to trigger early validation."""

    container_registry = None


class ContainerRegistryStubNoCreds:
    """Container registry stub with missing credentials."""

    def __init__(self):
        self.credentials = None


class StackStubWithRegistryNoCreds:
    """Stack stub with a container registry but no credentials."""

    def __init__(self):
        self.container_registry = ContainerRegistryStubNoCreds()


def test_build_modal_image_raises_when_no_registry() -> None:
    with pytest.raises(RuntimeError) as e:
        build_modal_image(
            "repo/image:tag", StackStubNoRegistry(), environment=None
        )
    assert "No Container registry found in the stack" in str(e.value)


def test_build_modal_image_raises_when_no_credentials() -> None:
    with pytest.raises(RuntimeError) as e:
        build_modal_image(
            "repo/image:tag", StackStubWithRegistryNoCreds(), environment=None
        )
    assert "No Docker credentials found for the container registry" in str(
        e.value
    )


def test_get_modal_stack_validator_returns_stackvalidator_instance() -> None:
    validator = get_modal_stack_validator()
    assert isinstance(validator, StackValidator)
    # Ensure the validator exposes a validate-like callable (public contract)
    assert hasattr(validator, "validate") and callable(validator.validate)
