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
from zenml.enums import ExecutionStatus, StackComponentType  # noqa: E402
from zenml.integrations.modal import sandbox_utils  # noqa: E402
from zenml.integrations.modal.flavors import (  # noqa: E402
    ModalOrchestratorConfig,
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.orchestrators import (  # noqa: E402
    modal_orchestrator as modal_orchestrator_module,
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
            resource_settings=ResourceSettingsStub(),
        ),
        step_configurations={"train": train_step},
    )


def _make_stack(registry_credentials=None):
    return SimpleNamespace(
        container_registry=SimpleNamespace(credentials=registry_credentials),
    )


def _make_placeholder_run():
    return SimpleNamespace(
        id=uuid4(),
        name="run-name",
        run_metadata={},
    )


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
    published = []
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

    def publish_pipeline_run_metadata_stub(*args, **kwargs):
        published.append((args, kwargs))

    monkeypatch.setattr(
        modal_orchestrator_module,
        "publish_pipeline_run_metadata",
        publish_pipeline_run_metadata_stub,
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
    assert placeholder_run.run_metadata == result.metadata
    assert published == [
        (
            (),
            {
                "pipeline_run_id": placeholder_run.id,
                "pipeline_run_metadata": {orchestrator.id: result.metadata},
            },
        )
    ]

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
    assert recorded["secret_values"][-1] == {
        SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "secret-token"
    }


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


def test_submission_terminates_sandbox_when_metadata_publish_fails(
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

    def publish_pipeline_run_metadata_stub(*args, **kwargs):
        raise RuntimeError("server unavailable")

    monkeypatch.setattr(
        modal_orchestrator_module,
        "publish_pipeline_run_metadata",
        publish_pipeline_run_metadata_stub,
    )

    with pytest.raises(RuntimeError, match="server unavailable"):
        orchestrator.submit_dynamic_pipeline(
            snapshot=_make_snapshot(is_dynamic=True),
            stack=_make_stack(),
            environment={},
            placeholder_run=placeholder_run,
        )

    assert recorded["created_sandboxes"][0].terminate_calls == 1


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
        config=SimpleNamespace(resource_settings=resource_settings),
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
    assert sandbox_kwargs["env"] == {"PLAIN": "value"}
    assert recorded["secret_values"] == [
        {SENSITIVE_ZENML_STORE_API_TOKEN_ENV_KEY: "secret-token"}
    ]


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


def test_fetch_status_maps_terminal_sandbox_to_stopped_for_stopping_run(
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

    assert pipeline_status == ExecutionStatus.STOPPED
    assert step_statuses is None


def test_isolated_step_status_maps_terminal_sandbox_to_stopped(monkeypatch):
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
        == ExecutionStatus.STOPPED
    )


def test_stop_run_terminates_orchestration_first_and_unique_running_children(
    monkeypatch,
):
    from_id_sandboxes = {
        "orchestrator-sandbox": SandboxStub("orchestrator-sandbox", [None]),
        "child-running": SandboxStub("child-running", [None]),
        "child-complete": SandboxStub("child-complete", [0]),
        "fallback-child": SandboxStub("fallback-child", [None]),
    }
    recorded = _install_modal_sdk_stubs(
        monkeypatch, from_id_sandboxes=from_id_sandboxes
    )
    run = SimpleNamespace(
        id=uuid4(),
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

    _make_orchestrator()._stop_run(run)

    assert recorded["termination_order"][0] == "orchestrator-sandbox"
    assert recorded["termination_order"].count("child-running") == 1
    assert recorded["termination_order"].count("fallback-child") == 1
    assert "child-complete" not in recorded["termination_order"]
    assert from_id_sandboxes["orchestrator-sandbox"].terminate_calls == 1
    assert from_id_sandboxes["child-running"].terminate_calls == 1
    assert from_id_sandboxes["fallback-child"].terminate_calls == 1
    assert from_id_sandboxes["child-complete"].terminate_calls == 0


def test_get_orchestrator_run_id_reads_modal_environment(monkeypatch):
    monkeypatch.setenv(ENV_ZENML_MODAL_RUN_ID, "stable-run-id")

    assert _make_orchestrator().get_orchestrator_run_id() == "stable-run-id"


def test_get_orchestrator_run_id_raises_when_missing(monkeypatch):
    monkeypatch.delenv(ENV_ZENML_MODAL_RUN_ID, raising=False)

    with pytest.raises(RuntimeError, match=ENV_ZENML_MODAL_RUN_ID):
        _make_orchestrator().get_orchestrator_run_id()
