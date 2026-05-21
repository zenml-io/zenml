"""Tests for harness environment cleanup."""

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, Generator
from uuid import UUID, uuid4

from tests.harness.environment import TestEnvironment as _TestEnvironment
from zenml.enums import StackComponentType


class _Page:
    """Minimal page object for the pagination helper."""

    def __init__(self, items: list[Any]) -> None:
        self.index = 1
        self.total_pages = 1
        self.items = items


class _ZenStore:
    """Track destructive calls in the order they happen."""

    def __init__(self, calls: list[tuple[str, UUID]]) -> None:
        self.calls = calls

    def delete_stack(self, stack_id: UUID) -> None:
        """Track stack deletion."""
        self.calls.append(("stack", stack_id))

    def delete_stack_component(self, component_id: UUID) -> None:
        """Track stack component deletion."""
        self.calls.append(("component", component_id))


class _Client:
    """Small fake client with just the cleanup surface."""

    def __init__(
        self,
        calls: list[tuple[str, UUID]],
        stacks_by_component_id: dict[UUID, list[Any]],
    ) -> None:
        self.zen_store = _ZenStore(calls)
        self._stacks_by_component_id = stacks_by_component_id

    def list_stacks(self, component_id: UUID, **_: Any) -> _Page:
        """Return stacks for the requested component."""
        return _Page(self._stacks_by_component_id.get(component_id, []))


class _Deployment:
    """Fake running deployment that yields a client."""

    def __init__(self, client: _Client) -> None:
        self.client = client
        self.config = SimpleNamespace(disabled=False)
        self.is_running = True

    @contextmanager
    def connect(self) -> Generator[_Client, None, None]:
        """Yield the fake client."""
        yield self.client


class _Requirement:
    """Fake environment requirement."""

    def __init__(self, stacks: list[Any]) -> None:
        self.stacks = stacks

    def check_software_requirements(self) -> tuple[bool, None]:
        """Report that the requirement can be used."""
        return True, None


class _StackRequirement:
    """Fake stack component requirement."""

    def __init__(self, component: Any, *, external: bool = False) -> None:
        self.component = component
        self.external = external
        self.type = component.type
        self.name = component.name

    def find_stack_component(self, client: _Client) -> Any:
        """Return the configured component."""
        del client
        return self.component


def test_deprovision_deletes_stacks_before_components() -> None:
    """Leftover test stacks must not block environment component cleanup."""
    component = SimpleNamespace(
        id=uuid4(),
        name="mlflow-local",
        type=StackComponentType.EXPERIMENT_TRACKER,
    )
    default_stack = SimpleNamespace(id=uuid4(), name="default")
    leftover_stack = SimpleNamespace(id=uuid4(), name="pytest-leftover")
    calls: list[tuple[str, UUID]] = []
    client = _Client(
        calls=calls,
        stacks_by_component_id={
            component.id: [default_stack, leftover_stack],
        },
    )
    environment = _TestEnvironment(
        config=SimpleNamespace(
            name="remote-mysql-modal",
            disabled=False,
            compiled_requirements=[
                _Requirement([_StackRequirement(component)]),
            ],
        ),
        deployment=_Deployment(client),
    )

    environment.deprovision()

    assert calls == [
        ("stack", leftover_stack.id),
        ("component", component.id),
    ]
