"""Docker-orchestrator smoke tests for the server-backed integration lane."""

from typing import TYPE_CHECKING, Generator, Tuple

import pytest

from tests.harness.utils import setup_test_stack_session
from zenml._test_support.docker_orchestrator_smoke import smoke_pipeline
from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunResponse
from zenml.zen_stores.rest_zen_store import RestZenStore

if TYPE_CHECKING:
    from tests.harness.environment import TestEnvironment


@pytest.fixture(scope="module")
def docker_orchestrator_client(
    request: pytest.FixtureRequest,
    auto_environment: Tuple["TestEnvironment", Client],
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[Client, None, None]:
    """Return a client configured to use the active Docker test stack."""
    env, client = auto_environment
    no_cleanup = request.config.getoption("no_cleanup", False)

    with setup_test_stack_session(
        request=request,
        tmp_path_factory=tmp_path_factory,
        environment=env,
        client=client,
        clean_repo=True,
        check_requirements=False,
        no_cleanup=no_cleanup,
    ):
        # Client() picks up the stack registered by setup_test_stack_session.
        yield Client()


@pytest.fixture(scope="module")
def docker_orchestrator_run(
    docker_orchestrator_client: Client,
) -> Tuple[Client, PipelineRunResponse]:
    """Run a minimal two-step pipeline on the configured Docker stack."""
    pipeline_run = smoke_pipeline()
    stored_run = docker_orchestrator_client.get_pipeline_run(pipeline_run.id)
    return docker_orchestrator_client, stored_run


def test_docker_orchestrator_completes_pipeline_run(
    docker_orchestrator_run: Tuple[Client, PipelineRunResponse],
) -> None:
    """Verify the Docker orchestrator can complete a minimal run."""
    client, pipeline_run = docker_orchestrator_run

    assert isinstance(client.zen_store, RestZenStore)
    assert client.active_stack.orchestrator.flavor == "local_docker"
    # The module is gated on the synchronized Docker requirement in tests.yaml,
    # so the run should be completed by the time smoke_pipeline() returns.
    assert pipeline_run.status == ExecutionStatus.COMPLETED
    assert set(pipeline_run.steps) == {
        "smoke_constant_step",
        "smoke_increment_step",
    }
    assert all(
        step_run.status == ExecutionStatus.COMPLETED
        for step_run in pipeline_run.steps.values()
    )


def test_docker_orchestrator_persists_pipeline_outputs(
    docker_orchestrator_run: Tuple[Client, PipelineRunResponse],
) -> None:
    """Verify step outputs and run metadata are persisted in the store."""
    client, pipeline_run = docker_orchestrator_run

    assert pipeline_run.steps["smoke_constant_step"].output.load() == 7
    assert pipeline_run.steps["smoke_increment_step"].output.load() == 8
    assert client.list_pipeline_runs().total == 1
    assert client.list_run_steps().total == 2
