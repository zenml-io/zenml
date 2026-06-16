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

# ruff: noqa: D100,D102,D103,D107

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

pytest.importorskip("modal")

from zenml.constants import (  # noqa: E402
    METADATA_ORCHESTRATOR_RUN_ID,
    ORCHESTRATOR_DOCKER_IMAGE_KEY,
)
from zenml.enums import (  # noqa: E402
    ExecutionMode,
    ExecutionStatus,
    StackComponentType,
)
from zenml.exceptions import AuthorizationException  # noqa: E402
from zenml.integrations.modal import sandbox_utils  # noqa: E402
from zenml.integrations.modal.flavors import (  # noqa: E402
    ModalOrchestratorConfig,
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.orchestrators import (  # noqa: E402
    modal_orchestrator as modal_orchestrator_module,
)
from zenml.integrations.modal.orchestrators import (  # noqa: E402
    modal_orchestrator_entrypoint as modal_entrypoint_module,
)
from zenml.integrations.modal.orchestrators.modal_orchestrator import (  # noqa: E402
    ENV_ZENML_MODAL_APP_NAME,
    ENV_ZENML_MODAL_RUN_ID,
    MODAL_APP_NAME_METADATA_KEY,
    MODAL_ENVIRONMENT_METADATA_KEY,
    MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY,
    MODAL_SANDBOX_ID_METADATA_KEY,
    ModalOrchestrator,
    get_modal_app_name,
    get_static_step_sandbox_metadata_key,
)
from zenml.orchestrators.dag_runner import NodeStatus  # noqa: E402

SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY = (
    sandbox_utils.SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY
)


class ResourceSettingsStub:
    """Minimal resource settings object used by Modal runtime tests."""

    def __init__(self, gpu_count=0, cpu_count=2, memory_mb=1.2):
        self.gpu_count = gpu_count
        self.cpu_count = cpu_count
        self.memory_mb = memory_mb

    def get_memory(self, _unit):
        return self.memory_mb


class BuildStub:
    """Pipeline build object that returns pipeline or step images."""

    def __init__(self, *, pipeline_image=True):
        self.pipeline_image = pipeline_image
        self.requests = []

    def get_image(self, component_key, step=None):
        assert component_key == ORCHESTRATOR_DOCKER_IMAGE_KEY
        self.requests.append((component_key, step))
        if step is None and not self.pipeline_image:
            raise KeyError("No pipeline image")
        return f"registry.example.com/zenml:{step or 'pipeline'}"


class SandboxStub:
    """Small Modal sandbox stand-in."""

    def __init__(self, object_id, poll_values=None):
        self.object_id = object_id
        self.poll_values = list(poll_values or [None])
        self.terminate_calls = 0

    def poll(self):
        if len(self.poll_values) > 1:
            return self.poll_values.pop(0)
        return self.poll_values[0]

    def terminate(self):
        self.terminate_calls += 1


class ModalClientStub:
    """Small stand-in for an opened Modal client."""

    def __init__(self, name: str):
        self.name = name
        self.closed = False

    def is_closed(self) -> bool:
        return self.closed


class PageStub:
    """Small page stand-in for ZenML client list responses."""

    def __init__(self, items):
        self.items = list(items)
        self.total = len(self.items)


def _make_orchestrator(
    config: ModalOrchestratorConfig | None = None,
) -> ModalOrchestrator:
    return ModalOrchestrator(
        name="modal",
        id=uuid4(),
        config=config or ModalOrchestratorConfig(),
        flavor="modal",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _make_snapshot(*, schedule=None, is_dynamic=False, pipeline_image=True):
    train_step = SimpleNamespace(
        config=SimpleNamespace(
            resource_settings=ResourceSettingsStub(),
            docker_settings=SimpleNamespace(),
        ),
        spec=SimpleNamespace(upstream_steps=[]),
    )
    return SimpleNamespace(
        id=uuid4(),
        schedule=schedule,
        is_dynamic=is_dynamic,
        project_id=uuid4(),
        build=BuildStub(pipeline_image=pipeline_image),
        pipeline_configuration=SimpleNamespace(
            name="pipe",
            execution_mode=ExecutionMode.FAIL_FAST,
            resource_settings=ResourceSettingsStub(),
        ),
        step_configurations={"train": train_step},
    )


def _make_stack(registry_credentials=None):
    return SimpleNamespace(
        container_registry=SimpleNamespace(credentials=registry_credentials),
    )


class _PlaceholderRunStub:
    """Mimics `PipelineRunResponse` strictness for attribute writes.

    The real response model exposes `orchestrator_run_id` as a read-only
    property and rejects writes to undeclared attributes, so this stub must
    too — a permissive double would let the orchestrator mutate response
    objects in ways that crash against the real model.
    """

    __slots__ = ("id", "name", "run_metadata", "project_id")

    def __init__(self):
        self.id = uuid4()
        self.name = "run-name"
        self.run_metadata = {}
        self.project_id = None

    @property
    def orchestrator_run_id(self):
        return None


def _make_placeholder_run():
    return _PlaceholderRunStub()


def _install_modal_sdk_stubs(monkeypatch, *, from_id_sandboxes=None):
    recorded = {
        "secret_values": [],
        "created_sandboxes": [],
        "termination_order": [],
    }
    from_id_sandboxes = from_id_sandboxes or {}

    class ImageFactoryStub:
        @staticmethod
        def from_registry(image_name, **kwargs):
            recorded["image_name"] = image_name
            recorded["image_kwargs"] = kwargs
            return SimpleNamespace(image_name=image_name)

    class SecretFactoryStub:
        @staticmethod
        def from_dict(values):
            recorded["secret_values"].append(dict(values))
            return SimpleNamespace(values=dict(values))

    class AppFactoryStub:
        @staticmethod
        def lookup(*args, **kwargs):
            recorded["app_lookup"] = (args, kwargs)
            return SimpleNamespace(app_name=args[0])

    class SandboxFactoryStub:
        @staticmethod
        def create(*args, **kwargs):
            sandbox = SandboxStub(
                f"sandbox-{len(recorded['created_sandboxes']) + 1}",
                poll_values=recorded.get("next_poll_values", [None]),
            )
            recorded["sandbox_create"] = (args, kwargs)
            recorded["created_sandboxes"].append(sandbox)
            return sandbox

        @staticmethod
        def from_id(sandbox_id, **kwargs):
            recorded.setdefault("from_id_calls", []).append(
                (sandbox_id, kwargs)
            )
            sandbox = from_id_sandboxes[sandbox_id]

            original_terminate = sandbox.terminate

            def terminate_with_recording():
                recorded["termination_order"].append(sandbox_id)
                original_terminate()

            sandbox.terminate = terminate_with_recording
            return sandbox

    monkeypatch.setattr(
        modal_orchestrator_module.modal, "Image", ImageFactoryStub
    )
    monkeypatch.setattr(
        modal_orchestrator_module.modal, "Secret", SecretFactoryStub
    )
    monkeypatch.setattr(modal_orchestrator_module.modal, "App", AppFactoryStub)
    monkeypatch.setattr(
        modal_orchestrator_module.modal, "Sandbox", SandboxFactoryStub
    )
    return recorded


def test_static_submission_records_metadata_and_splits_secrets(monkeypatch):
    recorded = _install_modal_sdk_stubs(monkeypatch)
    run_updates = []
    placeholder_run = _make_placeholder_run()
    snapshot = _make_snapshot(pipeline_image=False)
    stack = _make_stack(registry_credentials=("user", "pass"))
    orchestrator = _make_orchestrator(
        ModalOrchestratorConfig(
            synchronous=False,
            modal_environment="prod",
        )
    )
    orchestrator.get_settings = lambda _obj: ModalOrchestratorSettings(
        synchronous=False,
        modal_environment="prod",
    )

    class ZenStoreStub:
        @staticmethod
        def update_run(**kwargs):
            run_updates.append(kwargs)

    class ClientStub:
        zen_store = ZenStoreStub()

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)

    # Resolve credentials deterministically so the test does not depend on the
    # machine's ambient Modal configuration.
    monkeypatch.setattr(
        modal_orchestrator_module.sandbox_utils,
        "resolve_modal_token_pair",
        lambda **_kwargs: ("ak-token-id", "as-token-secret"),
    )

    result = orchestrator.submit_pipeline(
        snapshot=snapshot,
        stack=stack,
        base_environment={
            "PLAIN": "value",
            SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "secret-token",
        },
        step_environments={},
        placeholder_run=placeholder_run,
    )

    assert result is not None
    assert result.wait_for_completion is None
    assert result.metadata == {
        METADATA_ORCHESTRATOR_RUN_ID: str(placeholder_run.id),
        MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "sandbox-1",
        MODAL_APP_NAME_METADATA_KEY: get_modal_app_name(
            str(placeholder_run.id)
        ),
        MODAL_ENVIRONMENT_METADATA_KEY: "prod",
    }
    assert placeholder_run.run_metadata == {}
    assert run_updates[0]["run_id"] == placeholder_run.id
    assert run_updates[0]["run_update"].orchestrator_run_id == str(
        placeholder_run.id
    )
    assert snapshot.build.requests == [
        (ORCHESTRATOR_DOCKER_IMAGE_KEY, None),
        (ORCHESTRATOR_DOCKER_IMAGE_KEY, "train"),
    ]
    assert recorded["image_name"] == "registry.example.com/zenml:train"
    assert recorded["image_kwargs"]["secret"].values == {
        "REGISTRY_USERNAME": "user",
        "REGISTRY_PASSWORD": "pass",
    }
    assert recorded["app_lookup"][0] == (
        get_modal_app_name(str(placeholder_run.id)),
    )
    assert recorded["app_lookup"][1]["environment_name"] == "prod"

    sandbox_args, sandbox_kwargs = recorded["sandbox_create"]
    assert "ModalOrchestratorEntrypointConfiguration" in " ".join(sandbox_args)
    assert sandbox_kwargs["env"]["PLAIN"] == "value"
    assert sandbox_kwargs["env"][ENV_ZENML_MODAL_RUN_ID] == str(
        placeholder_run.id
    )
    assert sandbox_kwargs["env"][
        ENV_ZENML_MODAL_APP_NAME
    ] == get_modal_app_name(str(placeholder_run.id))
    assert SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY not in sandbox_kwargs["env"]
    assert sandbox_utils.MODAL_TOKEN_ID_ENV_KEY not in sandbox_kwargs["env"]
    assert (
        sandbox_utils.MODAL_TOKEN_SECRET_ENV_KEY not in sandbox_kwargs["env"]
    )
    # Modal credentials are forwarded into the controller sandbox as part of the
    # runtime secret so the controller can create child sandboxes.
    assert recorded["secret_values"][-1] == {
        SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "secret-token",
        sandbox_utils.MODAL_TOKEN_ID_ENV_KEY: "ak-token-id",
        sandbox_utils.MODAL_TOKEN_SECRET_ENV_KEY: "as-token-secret",
    }


def test_supported_execution_modes_include_static_failure_modes():
    assert _make_orchestrator().supported_execution_modes == [
        ExecutionMode.FAIL_FAST,
        ExecutionMode.STOP_ON_FAILURE,
        ExecutionMode.CONTINUE_ON_FAILURE,
    ]


def test_orchestrator_modal_client_caches_and_rebuilds_explicit_client(
    monkeypatch,
):
    first_client = ModalClientStub("first")
    second_client = ModalClientStub("second")
    clients = [first_client, second_client]
    recorded = []

    class ModalClientModuleStub:
        @staticmethod
        def from_credentials(token_id, token_secret):
            recorded.append((token_id, token_secret))
            return clients.pop(0)

    monkeypatch.setattr(
        modal_orchestrator_module.sandbox_utils.modal,
        "Client",
        ModalClientModuleStub,
    )

    orchestrator = _make_orchestrator(
        ModalOrchestratorConfig(
            token_id="ak-test",
            token_secret="as-test",
        )
    )

    assert orchestrator.get_modal_client() is first_client
    assert orchestrator.get_modal_client() is first_client

    first_client.closed = True

    assert orchestrator.get_modal_client() is second_client
    assert recorded == [
        ("ak-test", "as-test"),
        ("ak-test", "as-test"),
    ]


@pytest.mark.parametrize("is_dynamic", [False, True])
def test_submission_rejects_schedules(is_dynamic):
    orchestrator = _make_orchestrator()
    snapshot = _make_snapshot(
        schedule=SimpleNamespace(), is_dynamic=is_dynamic
    )
    stack = _make_stack()

    with pytest.raises(RuntimeError, match="Scheduling .* is not supported"):
        if is_dynamic:
            orchestrator.submit_dynamic_pipeline(
                snapshot=snapshot,
                stack=stack,
                environment={},
                placeholder_run=_make_placeholder_run(),
            )
        else:
            orchestrator.submit_pipeline(
                snapshot=snapshot,
                stack=stack,
                base_environment={},
                step_environments={},
                placeholder_run=_make_placeholder_run(),
            )


def test_submission_returns_metadata_without_manual_metadata_publish(
    monkeypatch,
):
    recorded = _install_modal_sdk_stubs(monkeypatch)
    placeholder_run = _make_placeholder_run()
    orchestrator = _make_orchestrator(
        ModalOrchestratorConfig(synchronous=False)
    )
    orchestrator.get_settings = lambda _obj: ModalOrchestratorSettings(
        synchronous=False
    )

    class ZenStoreStub:
        @staticmethod
        def update_run(**kwargs):
            return None

    class ClientStub:
        zen_store = ZenStoreStub()

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)

    result = orchestrator.submit_dynamic_pipeline(
        snapshot=_make_snapshot(is_dynamic=True),
        stack=_make_stack(),
        environment={},
        placeholder_run=placeholder_run,
    )

    assert result is not None
    assert result.metadata[MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY] == (
        "sandbox-1"
    )
    assert recorded["created_sandboxes"][0].terminate_calls == 0


def test_dynamic_isolated_step_submission_publishes_step_metadata(monkeypatch):
    recorded = _install_modal_sdk_stubs(monkeypatch)
    published = []
    run_id = uuid4()
    step_run_id = uuid4()
    step_run = SimpleNamespace(run_metadata={})
    resource_settings = ResourceSettingsStub(
        gpu_count=2, cpu_count=4, memory_mb=2.1
    )

    class ClientStub:
        active_stack = _make_stack()

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_orchestrator_module,
        "publish_step_run_metadata",
        lambda *args, **kwargs: published.append((args, kwargs)),
    )
    monkeypatch.setenv(ENV_ZENML_MODAL_APP_NAME, "existing-app")

    def get_step_image(key):
        assert key == ORCHESTRATOR_DOCKER_IMAGE_KEY
        return "registry.example.com/zenml:step"

    step_run_info = SimpleNamespace(
        pipeline_step_name="train",
        snapshot=SimpleNamespace(id=uuid4()),
        step_run_id=step_run_id,
        run_id=run_id,
        run_name="run",
        pipeline=SimpleNamespace(name="pipe"),
        config=SimpleNamespace(
            command=None,
            resource_settings=resource_settings,
        ),
        step_run=step_run,
        get_image=get_step_image,
    )

    orchestrator = _make_orchestrator()
    orchestrator.get_settings = lambda _obj: ModalOrchestratorSettings(
        gpu="A100",
        modal_environment="prod",
    )

    orchestrator.submit_isolated_step(
        step_run_info,
        {
            "PLAIN": "value",
            SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "secret-token",
        },
    )

    assert published == [
        (
            (
                step_run_id,
                {
                    orchestrator.id: {
                        MODAL_SANDBOX_ID_METADATA_KEY: "sandbox-1",
                        MODAL_ENVIRONMENT_METADATA_KEY: "prod",
                    }
                },
            ),
            {},
        )
    ]
    assert step_run.run_metadata == {
        MODAL_SANDBOX_ID_METADATA_KEY: "sandbox-1",
        MODAL_ENVIRONMENT_METADATA_KEY: "prod",
    }
    assert recorded["app_lookup"][0] == ("existing-app",)

    sandbox_args, sandbox_kwargs = recorded["sandbox_create"]
    assert "StepOperatorEntrypointConfiguration" in " ".join(sandbox_args)
    assert sandbox_kwargs["gpu"] == "A100:2"
    assert sandbox_kwargs["cpu"] == 4
    assert sandbox_kwargs["memory"] == 3
    assert sandbox_kwargs["env"] == {
        "PLAIN": "value",
        ENV_ZENML_MODAL_RUN_ID: str(run_id),
        ENV_ZENML_MODAL_APP_NAME: "existing-app",
    }
    assert recorded["secret_values"] == [
        {SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "secret-token"}
    ]


def test_dynamic_isolated_step_submission_adds_default_modal_environment(
    monkeypatch,
):
    recorded = _install_modal_sdk_stubs(monkeypatch)
    run_id = uuid4()
    step_run_id = uuid4()

    class ClientStub:
        active_stack = _make_stack()

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_orchestrator_module,
        "publish_step_run_metadata",
        lambda *args, **kwargs: None,
    )
    monkeypatch.delenv(ENV_ZENML_MODAL_RUN_ID, raising=False)
    monkeypatch.delenv(ENV_ZENML_MODAL_APP_NAME, raising=False)

    step_run_info = SimpleNamespace(
        pipeline_step_name="train",
        snapshot=SimpleNamespace(id=uuid4()),
        step_run_id=step_run_id,
        run_id=run_id,
        config=SimpleNamespace(
            command=None,
            resource_settings=ResourceSettingsStub(),
        ),
        step_run=SimpleNamespace(run_metadata={}),
        get_image=lambda key: "registry.example.com/zenml:step",
    )
    orchestrator = _make_orchestrator()
    orchestrator.get_settings = lambda _obj: ModalOrchestratorSettings()

    orchestrator.submit_isolated_step(step_run_info, {})

    assert recorded["app_lookup"][0] == (get_modal_app_name(str(run_id)),)
    assert recorded["sandbox_create"][1]["env"] == {
        ENV_ZENML_MODAL_RUN_ID: str(run_id),
        ENV_ZENML_MODAL_APP_NAME: get_modal_app_name(str(run_id)),
    }


def test_fetch_status_uses_run_and_step_metadata(monkeypatch):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "step-sandbox": SandboxStub("step-sandbox", [0]),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.RUNNING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox"
        },
        steps={
            "train": SimpleNamespace(
                id=uuid4(),
                status=ExecutionStatus.RUNNING,
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "step-sandbox"},
            )
        },
    )

    pipeline_status, step_statuses = _make_orchestrator().fetch_status(
        run, include_steps=True
    )

    assert pipeline_status == ExecutionStatus.RUNNING
    assert step_statuses == {"train": ExecutionStatus.COMPLETED}


def test_fetch_status_uses_static_pipeline_metadata_when_step_metadata_missing(
    monkeypatch,
):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "fallback-step-sandbox": SandboxStub("fallback-step-sandbox", [0]),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.RUNNING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox",
            get_static_step_sandbox_metadata_key(
                "train"
            ): "fallback-step-sandbox",
        },
        steps={
            "train": SimpleNamespace(
                id=uuid4(),
                status=ExecutionStatus.RUNNING,
                run_metadata={},
            )
        },
    )

    pipeline_status, step_statuses = _make_orchestrator().fetch_status(
        run, include_steps=True
    )

    assert pipeline_status == ExecutionStatus.RUNNING
    assert step_statuses == {"train": ExecutionStatus.COMPLETED}


def test_fetch_status_refreshes_static_fallback_metadata_for_hydrated_run(
    monkeypatch,
):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "fresh-fallback-step-sandbox": SandboxStub(
            "fresh-fallback-step-sandbox", [0]
        ),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    run_id = uuid4()
    stale_run = SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.RUNNING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox",
        },
        steps={
            "train": SimpleNamespace(
                id=uuid4(),
                status=ExecutionStatus.RUNNING,
                run_metadata={},
            )
        },
    )
    fresh_run = SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.RUNNING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox",
            get_static_step_sandbox_metadata_key(
                "train"
            ): "fresh-fallback-step-sandbox",
        },
        steps=stale_run.steps,
    )

    class ClientStub:
        @staticmethod
        def get_pipeline_run(_run_id):
            return fresh_run

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)

    pipeline_status, step_statuses = _make_orchestrator().fetch_status(
        stale_run, include_steps=True
    )

    assert pipeline_status == ExecutionStatus.RUNNING
    assert step_statuses == {"train": ExecutionStatus.COMPLETED}


def test_fetch_status_reports_completed_sandbox_for_stopping_run(
    monkeypatch,
):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [0]),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.STOPPING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox"
        },
    )

    pipeline_status, step_statuses = _make_orchestrator().fetch_status(run)

    assert pipeline_status == ExecutionStatus.COMPLETED
    assert step_statuses is None


def test_fetch_status_reports_running_sandbox_for_stopping_run(monkeypatch):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.STOPPING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox"
        },
    )

    pipeline_status, step_statuses = _make_orchestrator().fetch_status(run)

    assert pipeline_status == ExecutionStatus.RUNNING
    assert step_statuses is None


def test_isolated_step_status_reports_failed_sandbox_for_stopping_step(
    monkeypatch,
):
    from_id_sandboxes = {
        "step-sandbox": SandboxStub("step-sandbox", [1]),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    step_run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.STOPPING,
        run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "step-sandbox"},
    )

    assert (
        _make_orchestrator().get_isolated_step_status(step_run)
        == ExecutionStatus.FAILED
    )


def test_isolated_step_status_reports_running_sandbox_for_stopping_step(
    monkeypatch,
):
    from_id_sandboxes = {
        "step-sandbox": SandboxStub("step-sandbox", [None]),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    step_run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.STOPPING,
        run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "step-sandbox"},
    )

    assert (
        _make_orchestrator().get_isolated_step_status(step_run)
        == ExecutionStatus.RUNNING
    )


def test_isolated_step_status_reports_running_sandbox_for_stopped_step(
    monkeypatch,
):
    from_id_sandboxes = {
        "step-sandbox": SandboxStub("step-sandbox", [None]),
    }
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes=from_id_sandboxes)
    step_run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.STOPPED,
        run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "step-sandbox"},
    )

    assert (
        _make_orchestrator().get_isolated_step_status(step_run)
        == ExecutionStatus.RUNNING
    )


def test_isolated_step_status_reports_failed_when_sandbox_fetch_fails(
    monkeypatch,
):
    _install_modal_sdk_stubs(monkeypatch, from_id_sandboxes={})
    step_run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.RUNNING,
        run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "missing-sandbox"},
    )

    assert (
        _make_orchestrator().get_isolated_step_status(step_run)
        == ExecutionStatus.FAILED
    )


def test_graceful_stop_run_leaves_sandboxes_for_controller_to_drain(
    monkeypatch,
):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "child-running": SandboxStub("child-running", [None]),
    }
    recorded = _install_modal_sdk_stubs(
        monkeypatch, from_id_sandboxes=from_id_sandboxes
    )
    run = SimpleNamespace(
        id=uuid4(),
        snapshot=SimpleNamespace(is_dynamic=False),
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: (
                "orchestrator-sandbox"
            ),
        },
        steps={
            "train": SimpleNamespace(
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-running"}
            ),
        },
    )

    class ClientStub:
        @staticmethod
        def get_pipeline_run(_run_id):
            raise AssertionError(
                "Graceful stop should let the remote controller drain the DAG."
            )

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    _make_orchestrator()._stop_run(run, graceful=True)

    assert recorded["termination_order"] == []
    assert from_id_sandboxes["orchestrator-sandbox"].terminate_calls == 0
    assert from_id_sandboxes["child-running"].terminate_calls == 0


def test_graceful_stop_run_uses_fetched_static_snapshot(monkeypatch):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "child-running": SandboxStub("child-running", [None]),
    }
    recorded = _install_modal_sdk_stubs(
        monkeypatch, from_id_sandboxes=from_id_sandboxes
    )
    run_id = uuid4()
    stale_run = SimpleNamespace(
        id=run_id, snapshot=None, run_metadata={}, steps={}
    )
    hydrated_run = SimpleNamespace(
        id=run_id,
        snapshot=SimpleNamespace(is_dynamic=False),
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: (
                "orchestrator-sandbox"
            ),
        },
        steps={
            "train": SimpleNamespace(
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-running"}
            ),
        },
    )
    fetched_run_ids = []

    class ClientStub:
        @staticmethod
        def get_pipeline_run(_run_id):
            fetched_run_ids.append(_run_id)
            return hydrated_run

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    _make_orchestrator()._stop_run(stale_run, graceful=True)

    assert fetched_run_ids == [run_id]
    assert recorded["termination_order"] == []
    assert from_id_sandboxes["orchestrator-sandbox"].terminate_calls == 0
    assert from_id_sandboxes["child-running"].terminate_calls == 0


def test_graceful_stop_run_force_stops_dynamic_runs(monkeypatch):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "child-running": SandboxStub("child-running", [None]),
    }
    recorded = _install_modal_sdk_stubs(
        monkeypatch, from_id_sandboxes=from_id_sandboxes
    )
    run_id = uuid4()
    run = SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.STOPPING,
        snapshot=SimpleNamespace(is_dynamic=True),
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: (
                "orchestrator-sandbox"
            ),
        },
        steps={
            "train": SimpleNamespace(
                id=uuid4(),
                status=ExecutionStatus.RUNNING,
                config=SimpleNamespace(step_operator=None),
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-running"},
            ),
        },
    )

    class ClientStub:
        @staticmethod
        def get_pipeline_run(_run_id):
            return run

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    _make_orchestrator()._stop_run(run, graceful=True)

    assert recorded["termination_order"].count("child-running") == 1
    assert recorded["termination_order"].count("orchestrator-sandbox") == 1


def test_stop_run_refreshes_and_terminates_children_before_orchestration(
    monkeypatch,
):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "child-running": SandboxStub("child-running", [None]),
        "child-complete": SandboxStub("child-complete", [0]),
        "fallback-child": SandboxStub("fallback-child", [None]),
        "late-child": SandboxStub("late-child", [None]),
    }
    recorded = _install_modal_sdk_stubs(
        monkeypatch, from_id_sandboxes=from_id_sandboxes
    )
    run_id = uuid4()
    stale_run = SimpleNamespace(id=run_id, run_metadata={}, steps={})
    first_refresh = SimpleNamespace(
        id=run_id,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox",
            get_static_step_sandbox_metadata_key("fallback"): "fallback-child",
        },
        steps={
            "train": SimpleNamespace(
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-running"}
            ),
            "eval": SimpleNamespace(
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-running"}
            ),
            "report": SimpleNamespace(
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-complete"}
            ),
        },
    )
    second_refresh = SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.STOPPING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: "orchestrator-sandbox",
            get_static_step_sandbox_metadata_key("late"): "late-child",
        },
        steps={},
    )
    refreshed_runs = iter(
        [first_refresh, second_refresh, second_refresh, second_refresh]
    )

    class ClientStub:
        @staticmethod
        def get_pipeline_run(_run_id):
            return next(refreshed_runs)

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    _make_orchestrator()._stop_run(stale_run)

    assert recorded["termination_order"].count("child-running") == 1
    assert recorded["termination_order"].count("fallback-child") == 1
    assert "child-complete" not in recorded["termination_order"]
    orchestration_index = recorded["termination_order"].index(
        "orchestrator-sandbox"
    )
    assert (
        recorded["termination_order"].index("child-running")
        < orchestration_index
    )
    assert (
        recorded["termination_order"].index("fallback-child")
        < orchestration_index
    )
    assert (
        recorded["termination_order"].index("late-child") > orchestration_index
    )
    assert from_id_sandboxes["orchestrator-sandbox"].terminate_calls == 1
    assert from_id_sandboxes["child-running"].terminate_calls == 1
    assert from_id_sandboxes["fallback-child"].terminate_calls == 1
    assert from_id_sandboxes["late-child"].terminate_calls == 1
    assert from_id_sandboxes["child-complete"].terminate_calls == 0


def test_stop_run_only_terminates_modal_resources(monkeypatch):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "child-running": SandboxStub("child-running", [None]),
    }
    recorded = _install_modal_sdk_stubs(
        monkeypatch, from_id_sandboxes=from_id_sandboxes
    )
    run_id = uuid4()
    refreshed_run = SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.STOPPING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: (
                "orchestrator-sandbox"
            ),
        },
        steps={
            "train": SimpleNamespace(
                id=uuid4(),
                status=ExecutionStatus.RUNNING,
                run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-running"},
                config=SimpleNamespace(step_operator=None),
            ),
            "report": SimpleNamespace(
                id=uuid4(),
                status=ExecutionStatus.COMPLETED,
                run_metadata={},
                config=SimpleNamespace(step_operator=None),
            ),
            "remote_train": SimpleNamespace(
                id=uuid4(),
                status=ExecutionStatus.RUNNING,
                run_metadata={},
                config=SimpleNamespace(step_operator="sagemaker"),
            ),
        },
    )

    class ClientStub:
        @staticmethod
        def get_pipeline_run(_run_id):
            return refreshed_run

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    stale_run = SimpleNamespace(id=run_id, run_metadata={}, steps={})
    _make_orchestrator()._stop_run(stale_run)

    assert recorded["termination_order"].count("child-running") == 1
    assert recorded["termination_order"].count("orchestrator-sandbox") == 1


def test_stop_run_terminates_after_late_failed_pipeline_status(
    monkeypatch,
):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "child-running": SandboxStub("child-running", [None]),
    }
    recorded = _install_modal_sdk_stubs(
        monkeypatch, from_id_sandboxes=from_id_sandboxes
    )
    run_id = uuid4()
    running_step = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.RUNNING,
        run_metadata={MODAL_SANDBOX_ID_METADATA_KEY: "child-running"},
        config=SimpleNamespace(step_operator=None),
    )
    active_run = SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.STOPPING,
        run_metadata={
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: (
                "orchestrator-sandbox"
            ),
        },
        steps={"train": running_step},
    )
    failed_run = SimpleNamespace(
        id=run_id,
        status=ExecutionStatus.FAILED,
        run_metadata=active_run.run_metadata,
        steps=active_run.steps,
    )
    refreshed_runs = iter([active_run, active_run, active_run, failed_run])

    class ClientStub:
        @staticmethod
        def get_pipeline_run(_run_id):
            return next(refreshed_runs)

    monkeypatch.setattr(modal_orchestrator_module, "Client", ClientStub)
    stale_run = SimpleNamespace(id=run_id, run_metadata={}, steps={})
    _make_orchestrator()._stop_run(stale_run)

    assert recorded["termination_order"].count("child-running") == 1
    assert recorded["termination_order"].count("orchestrator-sandbox") == 1


class StaticStepRunRequestFactoryStub:
    """Small step run request factory for static controller tests."""

    def __init__(self):
        self.created_requests = []
        self.populate_calls = []

    @staticmethod
    def has_caching_enabled(_step_name):
        return False

    def create_request(self, step_name):
        request = SimpleNamespace(
            step_name=step_name,
            status=ExecutionStatus.INITIALIZING,
            end_time=None,
        )
        self.created_requests.append(request)
        return request

    def populate_request(self, request, *, step_runs):
        self.populate_calls.append((request, dict(step_runs)))


def _make_static_controller(
    monkeypatch,
    *,
    listed_step_runs=None,
):
    pipeline_run = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        run_metadata={},
    )
    snapshot = _make_snapshot()
    active_stack = SimpleNamespace()
    orchestrator = _make_orchestrator()
    orchestrator.id = "modal-orchestrator-id"
    step_run_request_factory = StaticStepRunRequestFactoryStub()
    created_run_steps = []
    listed_step_runs = PageStub(listed_step_runs or [])

    class ZenStoreStub:
        @staticmethod
        def create_run_step(request):
            created_run_steps.append(request)
            return SimpleNamespace(id=uuid4(), status=request.status)

    class ClientStub:
        zen_store = ZenStoreStub()

        @staticmethod
        def list_run_steps(**_kwargs):
            return listed_step_runs

    monkeypatch.setattr(
        modal_entrypoint_module.env_utils,
        "get_runtime_environment",
        lambda **_kwargs: {"STEP_ENV": "step-value"},
    )

    controller = modal_entrypoint_module._StaticModalPipelineController(
        snapshot=snapshot,
        pipeline_run=pipeline_run,
        active_stack=active_stack,
        orchestrator=orchestrator,
        client=ClientStub(),
        shared_env={"SHARED_ENV": "shared-value"},
        step_run_request_factory=step_run_request_factory,
    )
    return SimpleNamespace(
        controller=controller,
        pipeline_run=pipeline_run,
        orchestrator=orchestrator,
        step_run_request_factory=step_run_request_factory,
        created_run_steps=created_run_steps,
    )


def test_static_entrypoint_reuses_run_with_matching_modal_run_id(
    monkeypatch,
):
    snapshot = _make_snapshot()
    pipeline_run = SimpleNamespace(
        id=uuid4(),
        orchestrator_run_id="modal-run-id",
    )

    class ZenStoreStub:
        @staticmethod
        def update_run(**_kwargs):
            raise AssertionError("Run should not be updated twice.")

    class ClientStub:
        zen_store = ZenStoreStub()

        @staticmethod
        def get_pipeline_run(run_id):
            assert run_id == pipeline_run.id
            return pipeline_run

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)

    config = modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration(
        [
            "--snapshot_id",
            str(snapshot.id),
            "--run_id",
            str(pipeline_run.id),
        ]
    )
    config._snapshot = snapshot

    assert (
        config._get_or_create_pipeline_run(
            snapshot_id=snapshot.id,
            modal_run_id="modal-run-id",
        )
        is pipeline_run
    )


def test_static_entrypoint_rejects_run_with_different_modal_run_id(
    monkeypatch,
):
    snapshot = _make_snapshot()
    pipeline_run = SimpleNamespace(
        id=uuid4(),
        orchestrator_run_id="other-modal-run-id",
    )

    class ZenStoreStub:
        @staticmethod
        def update_run(**_kwargs):
            raise AssertionError("Mismatched run should not be updated.")

    class ClientStub:
        zen_store = ZenStoreStub()

        @staticmethod
        def get_pipeline_run(run_id):
            assert run_id == pipeline_run.id
            return pipeline_run

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)

    config = modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration(
        [
            "--snapshot_id",
            str(snapshot.id),
            "--run_id",
            str(pipeline_run.id),
        ]
    )
    config._snapshot = snapshot

    with pytest.raises(RuntimeError, match="other-modal-run-id"):
        config._get_or_create_pipeline_run(
            snapshot_id=snapshot.id,
            modal_run_id="modal-run-id",
        )


def test_static_entrypoint_runs_dumb_dag_runner(monkeypatch):
    snapshot = _make_snapshot()
    pipeline_run = _make_placeholder_run()
    pipeline_run.project_id = snapshot.project_id
    orchestrator = _make_orchestrator()
    orchestrator.get_orchestrator_run_id = lambda: "modal-run-id"
    captured_runner_kwargs = {}
    finalized = []

    class ClientStub:
        active_stack = SimpleNamespace(orchestrator=orchestrator)

    class StepRunRequestFactoryStub:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DagRunnerStub:
        def __init__(self, **kwargs):
            captured_runner_kwargs.update(kwargs)

        @staticmethod
        def run():
            return {"train": NodeStatus.COMPLETED}

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration,
        "_get_or_create_pipeline_run",
        lambda self, **_kwargs: pipeline_run,
    )
    monkeypatch.setattr(
        modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration,
        "_finalize_pipeline_run",
        staticmethod(
            lambda pipeline_run_id, statuses: finalized.append(
                (pipeline_run_id, statuses)
            )
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module,
        "get_config_environment_vars",
        lambda **_kwargs: ({}, {}),
    )
    monkeypatch.setattr(
        modal_entrypoint_module,
        "StepRunRequestFactory",
        StepRunRequestFactoryStub,
    )
    monkeypatch.setattr(modal_entrypoint_module, "DagRunner", DagRunnerStub)

    config = modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration(
        ["--snapshot_id", str(snapshot.id)]
    )
    config._snapshot = snapshot

    config.run()

    assert "execution_mode" not in captured_runner_kwargs
    assert captured_runner_kwargs["interrupt_function"] is not None
    assert finalized == [(pipeline_run.id, {"train": NodeStatus.COMPLETED})]


@pytest.mark.parametrize(
    ("run_status", "expected_interrupt"),
    [
        (
            ExecutionStatus.STOPPING,
            modal_entrypoint_module.InterruptMode.GRACEFUL,
        ),
        (ExecutionStatus.STOPPED, modal_entrypoint_module.InterruptMode.FORCE),
        (ExecutionStatus.FAILED, modal_entrypoint_module.InterruptMode.FORCE),
    ],
)
def test_static_controller_interrupts_for_external_stop_or_failure(
    monkeypatch,
    run_status,
    expected_interrupt,
):
    setup = _make_static_controller(monkeypatch)
    setup.controller.client.get_pipeline_run = lambda **_kwargs: (
        SimpleNamespace(status=run_status)
    )

    assert setup.controller.should_interrupt_execution() == expected_interrupt


def test_start_step_sandbox_launches_sandbox_on_cache_miss(monkeypatch):
    setup = _make_static_controller(monkeypatch)
    sandbox = SandboxStub("step-sandbox-id")
    setup.step_run_request_factory.has_caching_enabled = lambda _step_name: (
        True
    )

    def populate_running_request(request, *, step_runs):
        request.status = ExecutionStatus.RUNNING
        setup.step_run_request_factory.populate_calls.append(
            (request, dict(step_runs))
        )

    setup.step_run_request_factory.populate_request = populate_running_request
    setup.orchestrator.create_static_step_sandbox = lambda **_kwargs: sandbox
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_pipeline_run_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        modal_entrypoint_module,
        "publish_cached_step_run",
        lambda *_args, **_kwargs: pytest.fail(
            "Cache miss must not publish a cached step run."
        ),
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])

    assert setup.controller.start_step_sandbox(dag_node) == NodeStatus.RUNNING
    assert (
        dag_node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] == "step-sandbox-id"
    )
    assert setup.step_run_request_factory.created_requests[0].status == (
        ExecutionStatus.RUNNING
    )
    assert sandbox.terminate_calls == 0


def test_start_step_sandbox_uses_cached_step_run_on_cache_hit(monkeypatch):
    setup = _make_static_controller(monkeypatch)
    cached_step_run = SimpleNamespace(
        id=uuid4(), status=ExecutionStatus.CACHED
    )
    setup.step_run_request_factory.has_caching_enabled = lambda _step_name: (
        True
    )

    def populate_cached_request(request, *, step_runs):
        request.status = ExecutionStatus.CACHED
        setup.step_run_request_factory.populate_calls.append(
            (request, dict(step_runs))
        )

    setup.step_run_request_factory.populate_request = populate_cached_request
    setup.orchestrator.create_static_step_sandbox = lambda **_kwargs: (
        pytest.fail("Cache hit must not start a Modal sandbox.")
    )
    published_cached_requests = []
    monkeypatch.setattr(
        modal_entrypoint_module,
        "publish_cached_step_run",
        lambda request, pipeline_run: (
            published_cached_requests.append((request, pipeline_run))
            or cached_step_run
        ),
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])

    assert (
        setup.controller.start_step_sandbox(dag_node) == NodeStatus.COMPLETED
    )
    assert published_cached_requests == [
        (
            setup.step_run_request_factory.created_requests[0],
            setup.pipeline_run,
        )
    ]
    assert setup.step_run_request_factory.created_requests[0].status == (
        ExecutionStatus.CACHED
    )
    assert setup.controller.step_runs == {"train": cached_step_run}
    assert MODAL_SANDBOX_ID_METADATA_KEY not in dag_node.metadata


def test_start_step_sandbox_tolerates_metadata_publish_failure(monkeypatch):
    """A step metadata publish error must not kill the new sandbox."""
    setup = _make_static_controller(monkeypatch)
    sandbox = SandboxStub("step-sandbox-id")
    setup.orchestrator.create_static_step_sandbox = lambda **_kwargs: sandbox
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_pipeline_run_metadata",
        lambda *_args, **_kwargs: None,
    )

    def _raise_transient(_node):
        raise RuntimeError("transient server error")

    monkeypatch.setattr(
        setup.controller,
        "_publish_step_sandbox_metadata",
        _raise_transient,
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])

    assert setup.controller.start_step_sandbox(dag_node) == NodeStatus.RUNNING
    assert sandbox.terminate_calls == 0


def test_start_step_sandbox_tolerates_run_metadata_publish_failure(
    monkeypatch,
):
    setup = _make_static_controller(monkeypatch)
    sandbox = SandboxStub("step-sandbox-id")
    setup.orchestrator.create_static_step_sandbox = lambda **_kwargs: sandbox

    def raise_metadata_publish_error(*_args, **_kwargs):
        raise RuntimeError("server unavailable")

    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_pipeline_run_metadata",
        raise_metadata_publish_error,
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])

    assert setup.controller.start_step_sandbox(dag_node) == NodeStatus.RUNNING
    assert sandbox.terminate_calls == 0


def test_static_controller_start_sandbox_records_run_and_step_metadata(
    monkeypatch,
):
    step_run_id = uuid4()
    published_pipeline_metadata = []
    published_step_metadata = []
    created_environments = []
    step_run = SimpleNamespace(
        id=step_run_id,
        status=ExecutionStatus.RUNNING,
    )
    setup = _make_static_controller(
        monkeypatch,
        listed_step_runs=[step_run],
    )

    def create_static_step_sandbox(**kwargs):
        created_environments.append(kwargs["environment"])
        return SandboxStub("step-sandbox-id")

    setup.orchestrator.create_static_step_sandbox = create_static_step_sandbox
    setup.orchestrator.get_settings = lambda _step: ModalOrchestratorSettings(
        modal_environment="prod"
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_pipeline_run_metadata",
        lambda *args, **kwargs: published_pipeline_metadata.append(
            (args, kwargs)
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_step_run_metadata",
        lambda *args, **kwargs: published_step_metadata.append((args, kwargs)),
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])

    assert setup.controller.start_step_sandbox(dag_node) == NodeStatus.RUNNING

    assert created_environments == [
        {"SHARED_ENV": "shared-value", "STEP_ENV": "step-value"}
    ]
    assert (
        dag_node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] == "step-sandbox-id"
    )
    assert (
        dag_node.metadata[modal_entrypoint_module.NODE_METADATA_PUBLISHED_KEY]
        is True
    )
    assert published_pipeline_metadata == [
        (
            (
                setup.pipeline_run.id,
                {
                    "modal-orchestrator-id": {
                        get_static_step_sandbox_metadata_key(
                            "train"
                        ): "step-sandbox-id"
                    }
                },
            ),
            {},
        )
    ]
    assert published_step_metadata == [
        (
            (
                step_run_id,
                {
                    "modal-orchestrator-id": {
                        MODAL_SANDBOX_ID_METADATA_KEY: "step-sandbox-id",
                        MODAL_ENVIRONMENT_METADATA_KEY: "prod",
                    }
                },
            ),
            {},
        )
    ]


def test_static_controller_failed_sandbox_respects_successful_step_run(
    monkeypatch,
):
    step_run = SimpleNamespace(status=ExecutionStatus.COMPLETED)
    setup = _make_static_controller(
        monkeypatch,
        listed_step_runs=[step_run],
    )
    setup.orchestrator.get_modal_client = lambda: "modal-client"
    monkeypatch.setattr(
        modal_entrypoint_module.sandbox_utils,
        "get_sandbox_status",
        lambda *_args, **_kwargs: ExecutionStatus.FAILED,
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])
    dag_node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] = "step-sandbox-id"
    dag_node.metadata[modal_entrypoint_module.NODE_METADATA_PUBLISHED_KEY] = (
        True
    )

    assert (
        setup.controller.check_step_sandbox(dag_node) == NodeStatus.COMPLETED
    )
    assert setup.created_run_steps == []


def test_check_step_sandbox_tolerates_metadata_publish_failure(monkeypatch):
    """A transient metadata publish error must not fail a healthy node."""
    setup = _make_static_controller(monkeypatch)
    setup.orchestrator.get_modal_client = lambda: "modal-client"
    monkeypatch.setattr(
        modal_entrypoint_module.sandbox_utils,
        "get_sandbox_status",
        lambda *_args, **_kwargs: ExecutionStatus.RUNNING,
    )

    def _raise_transient(_node):
        raise RuntimeError("transient server error")

    monkeypatch.setattr(
        setup.controller,
        "_publish_step_sandbox_metadata",
        _raise_transient,
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])
    dag_node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] = "step-sandbox-id"

    assert setup.controller.check_step_sandbox(dag_node) == NodeStatus.RUNNING


def test_step_metadata_publish_attempts_are_throttled(monkeypatch):
    setup = _make_static_controller(monkeypatch)
    attempts = []
    monkeypatch.setattr(
        setup.controller,
        "_publish_step_sandbox_metadata",
        lambda _node: attempts.append(1) or False,
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])
    dag_node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] = "step-sandbox-id"

    setup.controller._maybe_publish_step_sandbox_metadata(dag_node)
    setup.controller._maybe_publish_step_sandbox_metadata(dag_node)
    assert len(attempts) == 1

    dag_node.metadata[
        modal_entrypoint_module.NODE_METADATA_PUBLISH_ATTEMPTED_AT_KEY
    ] -= (
        modal_entrypoint_module.STEP_METADATA_PUBLISH_RETRY_INTERVAL_SECONDS
        + 1
    )
    setup.controller._maybe_publish_step_sandbox_metadata(dag_node)
    assert len(attempts) == 2


def test_static_controller_failed_sandbox_publishes_failed_step_run(
    monkeypatch,
):
    setup = _make_static_controller(monkeypatch, listed_step_runs=[])
    setup.orchestrator.get_modal_client = lambda: "modal-client"
    monkeypatch.setattr(
        modal_entrypoint_module.sandbox_utils,
        "get_sandbox_status",
        lambda *_args, **_kwargs: ExecutionStatus.FAILED,
    )

    dag_node = modal_entrypoint_module.Node(id="train", upstream_nodes=[])
    dag_node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] = "step-sandbox-id"
    dag_node.metadata[modal_entrypoint_module.NODE_METADATA_PUBLISHED_KEY] = (
        True
    )

    assert setup.controller.check_step_sandbox(dag_node) == NodeStatus.FAILED

    assert len(setup.created_run_steps) == 1
    created_request = setup.created_run_steps[0]
    assert created_request.step_name == "train"
    assert created_request.status == ExecutionStatus.FAILED
    assert created_request.end_time is not None


def test_static_controller_finalize_raises_after_failed_child_publish(
    monkeypatch,
):
    pipeline_run_id = uuid4()
    step_run_id = uuid4()
    published = []

    class ClientStub:
        @staticmethod
        def get_pipeline_run(*args, **kwargs):
            return SimpleNamespace(
                id=pipeline_run_id,
                status=ExecutionStatus.RUNNING,
            )

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_entrypoint_module,
        "fetch_step_runs_by_names",
        lambda **_kwargs: {
            "train": SimpleNamespace(
                id=step_run_id,
                status=ExecutionStatus.RUNNING,
            )
        },
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_failed_step_run",
        lambda step_id: published.append(("step", step_id)),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_failed_pipeline_run",
        lambda run_id: published.append(("pipeline", run_id)),
    )

    with pytest.raises(RuntimeError, match="train"):
        modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration._finalize_pipeline_run(
            pipeline_run_id,
            {"train": NodeStatus.FAILED},
        )

    assert published == [
        ("step", step_run_id),
        ("pipeline", pipeline_run_id),
    ]


def test_static_controller_finalize_ignores_cancelled_children(
    monkeypatch,
):
    pipeline_run_id = uuid4()
    failed_step_run_id = uuid4()
    fetched_step_names = []
    published = []

    class ClientStub:
        @staticmethod
        def get_pipeline_run(*args, **kwargs):
            return SimpleNamespace(
                id=pipeline_run_id,
                status=ExecutionStatus.RUNNING,
            )

    def fetch_step_runs_by_names_stub(**kwargs):
        fetched_step_names.extend(kwargs["step_run_names"])
        return {
            "train": SimpleNamespace(
                id=failed_step_run_id,
                status=ExecutionStatus.PROVISIONING,
            )
        }

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_entrypoint_module,
        "fetch_step_runs_by_names",
        fetch_step_runs_by_names_stub,
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_failed_step_run",
        lambda step_id: published.append(("failed-step", step_id)),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_cancelled_step_run",
        lambda step_id: pytest.fail(
            "DAG cancelled nodes must not publish ZenML cancelled step status."
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_failed_pipeline_run",
        lambda run_id: published.append(("failed-pipeline", run_id)),
    )

    with pytest.raises(RuntimeError, match="train"):
        modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration._finalize_pipeline_run(
            pipeline_run_id,
            {
                "train": NodeStatus.FAILED,
                "eval": NodeStatus.CANCELLED,
            },
        )

    assert fetched_step_names == ["train"]
    assert published == [
        ("failed-step", failed_step_run_id),
        ("failed-pipeline", pipeline_run_id),
    ]


def test_static_controller_finalize_ignores_cancelled_only_run(
    monkeypatch,
):
    pipeline_run_id = uuid4()
    published = []

    class ClientStub:
        @staticmethod
        def get_pipeline_run(*args, **kwargs):
            return SimpleNamespace(
                id=pipeline_run_id,
                status=ExecutionStatus.RUNNING,
            )

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_entrypoint_module,
        "fetch_step_runs_by_names",
        lambda **_kwargs: pytest.fail(
            "Cancelled DAG nodes must not be fetched as failed steps."
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_failed_step_run",
        lambda step_id: pytest.fail(
            "Cancelled DAG nodes must not publish failed step status."
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_cancelled_step_run",
        lambda step_id: pytest.fail(
            "DAG cancelled nodes must not publish ZenML cancelled step status."
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_successful_pipeline_run",
        lambda run_id: published.append(("successful-pipeline", run_id)),
    )

    modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration._finalize_pipeline_run(
        pipeline_run_id,
        {"train": NodeStatus.CANCELLED},
    )

    assert published == [("successful-pipeline", pipeline_run_id)]


def test_static_controller_finalize_logs_skipped_without_failing_steps(
    monkeypatch,
):
    pipeline_run_id = uuid4()
    published = []

    class ClientStub:
        @staticmethod
        def get_pipeline_run(*args, **kwargs):
            return SimpleNamespace(
                id=pipeline_run_id,
                status=ExecutionStatus.RUNNING,
            )

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_entrypoint_module,
        "fetch_step_runs_by_names",
        lambda **_kwargs: pytest.fail(
            "Skipped DAG nodes must not be fetched as failed steps."
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_failed_step_run",
        lambda step_id: pytest.fail(
            "Skipped DAG nodes must not publish failed step status."
        ),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_successful_pipeline_run",
        lambda run_id: published.append(("successful-pipeline", run_id)),
    )

    modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration._finalize_pipeline_run(
        pipeline_run_id,
        {"train": NodeStatus.SKIPPED},
    )

    assert published == [("successful-pipeline", pipeline_run_id)]


def test_static_controller_finalize_raises_failed_child_on_auth_error(
    monkeypatch,
):
    pipeline_run_id = uuid4()

    class ClientStub:
        @staticmethod
        def get_pipeline_run(*args, **kwargs):
            raise AuthorizationException("not authorized")

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)

    with pytest.raises(RuntimeError, match="train"):
        modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration._finalize_pipeline_run(
            pipeline_run_id,
            {"train": NodeStatus.FAILED},
        )


def test_static_controller_finalize_stopping_run_does_not_raise(
    monkeypatch,
):
    pipeline_run_id = uuid4()
    published = []

    class ClientStub:
        @staticmethod
        def get_pipeline_run(*args, **kwargs):
            return SimpleNamespace(status=ExecutionStatus.STOPPING)

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_pipeline_run_status_update",
        lambda run_id, status: published.append((run_id, status)),
    )

    modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration._finalize_pipeline_run(
        pipeline_run_id,
        {"train": NodeStatus.CANCELLED},
    )

    assert published == [(pipeline_run_id, ExecutionStatus.STOPPED)]


def test_static_controller_finalize_respects_late_stop_request(
    monkeypatch,
):
    pipeline_run_id = uuid4()
    published = []
    refreshed_statuses = iter(
        [ExecutionStatus.RUNNING, ExecutionStatus.STOPPING]
    )

    class ClientStub:
        @staticmethod
        def get_pipeline_run(*args, **kwargs):
            return SimpleNamespace(
                id=pipeline_run_id,
                status=next(refreshed_statuses),
            )

    monkeypatch.setattr(modal_entrypoint_module, "Client", ClientStub)
    monkeypatch.setattr(
        modal_entrypoint_module,
        "fetch_step_runs_by_names",
        lambda **_kwargs: {},
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_pipeline_run_status_update",
        lambda run_id, status: published.append(("status", run_id, status)),
    )
    monkeypatch.setattr(
        modal_entrypoint_module.publish_utils,
        "publish_failed_pipeline_run",
        lambda run_id: published.append(("failed", run_id)),
    )

    modal_entrypoint_module.ModalOrchestratorEntrypointConfiguration._finalize_pipeline_run(
        pipeline_run_id,
        {"train": NodeStatus.FAILED},
    )

    assert published == [("status", pipeline_run_id, ExecutionStatus.STOPPED)]


def test_resolve_modal_token_pair_prefers_component_config(monkeypatch):
    def _fail_ambient(_key):
        raise AssertionError(
            "Ambient Modal config must not be read when the component token "
            "is configured."
        )

    monkeypatch.setattr("modal.config.config.get", _fail_ambient)

    assert sandbox_utils.resolve_modal_token_pair(
        token_id="ak-config",
        token_secret="as-config",
    ) == ("ak-config", "as-config")


def test_resolve_modal_token_pair_falls_back_to_ambient_config(monkeypatch):
    ambient = {"token_id": "ak-ambient", "token_secret": "as-ambient"}
    monkeypatch.setattr(
        "modal.config.config.get",
        lambda key: ambient.get(key),
    )

    assert sandbox_utils.resolve_modal_token_pair(
        token_id=None,
        token_secret=None,
    ) == ("ak-ambient", "as-ambient")


def test_resolve_modal_token_pair_returns_none_without_credentials(
    monkeypatch,
):
    monkeypatch.setattr("modal.config.config.get", lambda _key: None)

    assert (
        sandbox_utils.resolve_modal_token_pair(
            token_id=None,
            token_secret=None,
        )
        is None
    )


def test_inject_modal_credentials_warns_and_skips_without_credentials(
    monkeypatch,
):
    monkeypatch.setattr(
        modal_orchestrator_module.sandbox_utils,
        "resolve_modal_token_pair",
        lambda **_kwargs: None,
    )
    environment: dict[str, str] = {}

    _make_orchestrator()._inject_modal_credentials(environment)

    assert sandbox_utils.MODAL_TOKEN_ID_ENV_KEY not in environment
    assert sandbox_utils.MODAL_TOKEN_SECRET_ENV_KEY not in environment


def test_get_orchestrator_run_id_reads_modal_environment(monkeypatch):
    monkeypatch.setenv(ENV_ZENML_MODAL_RUN_ID, "stable-run-id")

    assert _make_orchestrator().get_orchestrator_run_id() == "stable-run-id"


def test_get_orchestrator_run_id_raises_when_missing(monkeypatch):
    monkeypatch.delenv(ENV_ZENML_MODAL_RUN_ID, raising=False)

    with pytest.raises(RuntimeError, match=ENV_ZENML_MODAL_RUN_ID):
        _make_orchestrator().get_orchestrator_run_id()
